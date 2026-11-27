"""Bounded HTTP acquisition and qualified reuse of retained representations."""
from __future__ import annotations

from dataclasses import replace
from datetime import datetime, timezone
from pathlib import PurePosixPath
from hashlib import sha256
from urllib.parse import urlsplit

from stratbox.core.execution.errors import ExecutionFailure
from stratbox.shared.data.materials import RetainedRepresentation, representation_identity
from stratbox.shared.data.values import FetchEvidence, ImmutableMaterialRef, Material, request_identity
from ._settings import _option


def _headers(values):
    admitted = {'content-type','content-length','content-encoding','etag','last-modified','vary','retry-after'}
    return {str(key).lower():value for key,value in values.items()
            if str(key).lower() in admitted and isinstance(value,str) and len(value) <= 8192
            and not any(ord(char) < 32 or ord(char) == 127 for char in value)}


def _vary(headers):
    return tuple(sorted({name.strip().lower() for name in headers.get('vary','').split(',') if name.strip()}))


def _exchange(request, context):
    from stratbox.core.network.contracts import HttpRequest, HttpsEndpoint
    parts = urlsplit(request.url)
    remaining = context.remaining_seconds() if hasattr(context,'remaining_seconds') else request.timeout
    return HttpRequest(request.method, request.url,
        (HttpsEndpoint(parts.hostname, parts.path or '/', allow_query=True),),
        headers=request.headers, body=request.body, form_fields=request.form,
        deadline_seconds=min(request.timeout, remaining), max_response_bytes=request.max_bytes,
        read_only_post=request.method == 'POST' and request.read_only, budget=getattr(context,'budget',None))


def _evidence(request, response, identity, *, retained=None):
    headers = _headers(getattr(response,'headers',{}))
    if retained:
        headers = {**dict(retained.validators),**({'vary':','.join(retained.vary)} if retained.vary else {}),**headers}
    parts = urlsplit(request.url)
    actual = getattr(response,'effective_locator_safe',None)
    effective_parts = urlsplit(actual) if actual else parts
    actual_identity = getattr(response,'target_sha256',None)
    if actual_identity is None and actual and (effective_parts.path not in {'','/'} or effective_parts.query):
        actual_identity = sha256(actual.encode()).hexdigest()
    vary = _vary(headers) or (retained.vary if retained else ())
    try:
        representation = representation_identity(request,vary=vary)
    except ValueError:
        representation = None
    return FetchEvidence(request_identity(request), getattr(response,'observed_at_utc',datetime.now(timezone.utc)),
        getattr(response,'status_code',200), identity, headers,
        request.observation_id or getattr(response,'observation_id',''),
        # Durable acquisition evidence binds the actual target by hash. Even a
        # hostname is unnecessary in generic journal facts and progress logs.
        None, getattr(response,'origin_assurance','provider_reported'),
        getattr(response,'transport_assurance',None), getattr(response,'route_id',None),
        actual_identity,getattr(response,'logical_target_sha256',None),
        'retained_validation' if retained else 'body', representation,
        retained.reference.effect_id if retained else None)


def _retained_basis(request, retained, context):
    if not isinstance(retained, RetainedRepresentation) or not retained.validators or request.method != 'GET':
        return None
    if retained.assurance != 'provider_validated':
        return None
    try:
        if representation_identity(request,vary=retained.vary) != retained.representation_identity:
            return None
        service = getattr(context,'service',None)
        receipt = service.lookup_effect(retained.reference.effect_id) if service else None
        if receipt is None or receipt.status != 'confirmed':
            return None
        original = receipt.value
        previous = retained.evidence
        if previous is not None:
            verifier = getattr(context,'verify_acquisition_evidence',None)
            if not isinstance(previous,FetchEvidence) or not verifier or not verifier(previous):
                return None
        else:
            previous = next((item for item in reversed(getattr(original,'lineage',()))
                            if isinstance(item,FetchEvidence)),None)
            verifier = getattr(context,'verify_acquisition_evidence',None)
            if previous is None or not verifier or not verifier(previous):
                return None
        if (previous is None or previous.material_identity != retained.reference.identity
                or previous.representation_identity != retained.representation_identity
                or dict(retained.validators) != {key:value for key,value in previous.headers.items() if key in {'etag','last-modified'}}
                or retained.vary != _vary(previous.headers)
                or retained.request_identity and retained.request_identity != previous.request_identity):
            return None
        with context.open_material(retained.reference):
            pass
    except (OSError, ValueError, TypeError):
        return None
    return retained


def _conditional(request, retained):
    headers = {key:value for key,value in request.headers.items()
               if key.lower() not in {'if-none-match','if-modified-since'}}
    if retained:
        if 'etag' in retained.validators:
            headers['If-None-Match'] = retained.validators['etag']
        elif 'last-modified' in retained.validators:
            headers['If-Modified-Since'] = retained.validators['last-modified']
    return replace(request,headers=headers)


def _account(context, response, size, before):
    budget = getattr(context,'budget',None)
    if budget is None:
        return
    for resource, amount in (('wire_bytes',getattr(response,'wire_size',None) or size),('decoded_bytes',size)):
        spent = budget.used(resource) - before.get(resource,0)
        if amount > spent:
            budget.charge(resource,amount-spent)


def _attempt(request, placement, context):
    provider = context.provider('http')
    context.checkpoint()
    budget = getattr(context,'budget',None)
    before = dict(budget.usage()) if budget else {}
    if budget and not getattr(provider,'accounts_http_budget',False):
        budget.charge('requests',1)
    metadata = {'url':request.url,'filename':PurePosixPath(urlsplit(request.url).path).name,
                **dict(request.metadata)}
    if placement == 'staged':
        from stratbox.core.network.contracts import HttpStreamResponse
        send = getattr(provider,'exchange_into',None)
        if not callable(send):
            raise ExecutionFailure('http.streaming_provider_required')
        with context.stage(source_id=request.source_id,metadata=metadata) as stage:
            class Sink:
                def write(self,data):
                    if stage.tell() + len(data) > request.max_bytes:
                        raise ExecutionFailure('http.response_limit')
                    return stage.write(data)
                def seek(self,*args): return stage.seek(*args)
                def tell(self): return stage.tell()
                def truncate(self,*args): return stage.truncate(*args)
                def flush(self): return stage.flush()
            def cancelled():
                context.checkpoint()
                return False
            response = send(_exchange(request,context),Sink(),cancelled=cancelled)
            if not isinstance(response,HttpStreamResponse):
                raise ExecutionFailure('http.streaming_response_required')
            observed, identity = response.response, response.identity
            if observed.status_code == 304:
                if identity.size or stage.tell():
                    raise ExecutionFailure('http.304_body_forbidden')
                _account(context,observed,0,before)
                return None,observed
            if not 200 <= observed.status_code < 300:
                raise ExecutionFailure('http.response_failed:' + str(observed.status_code))
            if identity.size > request.max_bytes:
                raise ExecutionFailure('http.response_limit')
            evidence = _evidence(request,observed,identity)
            stage.properties['media_type'] = _headers(observed.headers).get('content-type','application/octet-stream').split(';')[0]
            material = stage.seal(lineage=(evidence,))
            if material.identity != identity:
                raise ExecutionFailure('http.stream_identity_mismatch')
            _account(context,observed,identity.size,before)
            return material,observed
    if hasattr(provider,'fetch'):
        response = provider.fetch(request)
    elif callable(provider):
        response = provider(request)
    else:
        send = getattr(provider,'exchange',None) or getattr(provider,'request',None) or getattr(provider,'send',None)
        if not callable(send):
            raise ExecutionFailure('http.provider_protocol')
        response = send(_exchange(request,context))
    status = getattr(response,'status_code',200)
    body = response if isinstance(response,bytes) else response.data if isinstance(response,Material) else getattr(response,'body',getattr(response,'content',None))
    if status == 304:
        if body:
            raise ExecutionFailure('http.304_body_forbidden')
        _account(context,response,0,before)
        return None,response
    if not 200 <= status < 300 or not isinstance(body,bytes):
        raise ExecutionFailure('http.response_failed:' + str(status))
    if len(body) > request.max_bytes:
        raise ExecutionFailure('http.response_limit')
    media = _headers(getattr(response,'headers',{})).get('content-type',getattr(response,'media_type','application/octet-stream')).split(';')[0]
    material = Material(body,media,request.source_id,metadata=metadata)
    evidence = _evidence(request,response,material.identity)
    material = replace(material,lineage=(evidence,))
    _account(context,response,len(body),before)
    return material,response


def material_fetch(inputs, settings, context):
    request = inputs['request']
    if request.method not in {'GET','POST'} or request.method == 'POST' and not request.read_only:
        raise ExecutionFailure('http.read_only_request_required')
    placement = _option(context,settings,'placement','buffered')
    if placement not in {'buffered','staged'}:
        raise ExecutionFailure('material.placement_invalid')
    retained = _retained_basis(request,inputs.get('retained'),context)
    effective = _conditional(request,retained)
    material,response = _attempt(effective,placement,context)
    if getattr(response,'status_code',200) == 304:
        headers = _headers(getattr(response,'headers',{}))
        valid = retained is not None and ('vary' not in headers or _vary(headers) == retained.vary)
        valid = valid and all(name not in headers or headers[name] == value for name,value in retained.validators.items())
        if valid:
            # The original was verified immediately before the request. Repeat
            # verification closes a deletion/corruption window during network IO.
            try:
                with context.open_material(retained.reference):
                    pass
            except (OSError,ValueError):
                valid = False
        if valid:
            evidence = _evidence(effective,response,retained.reference.identity,retained=retained)
            return {'material':retained.reference,'evidence':evidence,'request':effective}
        # At most one unconditional retry, including an unsolicited 304.
        effective = _conditional(request,None)
        material,response = _attempt(effective,placement,context)
        if getattr(response,'status_code',200) == 304:
            raise ExecutionFailure('http.retained_body_required')
    evidence = material.lineage[-1]
    return {'material':material,'evidence':evidence,'request':effective}


def material_receive(inputs, settings, context):
    """Retain a streaming acquisition under the same declared effect authority."""
    from .artifacts import artifact_commit
    acquired = material_fetch(inputs,settings,_PlacementContext(context,'staged'))
    # A retained 304 supplies bytes for the current request. It does not fulfill
    # a different destination merely because its earlier retention succeeded.
    retained = artifact_commit({'material':acquired['material'],'destination':inputs['destination']},settings,context)
    reference,receipt = retained['reference'],retained['receipt']
    return {'reference':reference,'evidence':acquired['evidence'],'receipt':receipt,'request':acquired['request']}


class _PlacementContext:
    """Use a streaming entrance without altering the actual command context."""
    def __init__(self,context,placement):
        self._context = context
        self.parameters = {**context.parameters,'placement':placement}
    def __getattr__(self,name):
        return getattr(self._context,name)
