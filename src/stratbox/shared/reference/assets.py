"""Integrity-checked reference contents with factual dates and exact identities."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import date
from importlib import resources
import json
from pathlib import PurePosixPath
import re
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


class ReferenceError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class ReferenceAsset:
    role: str
    package: str
    path: str
    media_type: str
    identity: ByteIdentity
    required: bool = True
    publisher: str | None = None
    curator: str | None = None
    source_url: str | None = None
    origin_kind: str | None = None


@dataclass(frozen=True, slots=True)
class ReferenceDefinition:
    reference_id: str
    assets: tuple[ReferenceAsset, ...]
    publisher: str | None = None
    source_url: str | None = None
    curator: str | None = None
    published_at: date | None = None
    effective_from: date | None = None
    effective_to: date | None = None


@dataclass(frozen=True, slots=True)
class LoadedReference:
    reference: ReferenceDefinition
    snapshot_identity: ByteIdentity

    def asset(self, role):
        for asset in self.reference.assets:
            if asset.role == role:
                return asset
        raise ReferenceError('Undeclared reference role: '+str(role))

    def read(self, role, *, inputs=None):
        asset = self.asset(role)
        try:
            data = resources.files(asset.package).joinpath('_resources',*asset.path.split('/')).read_bytes()
        except FileNotFoundError as error:
            raise ReferenceError('Reference asset missing: '+self.reference.reference_id+':'+role) from error
        if ByteIdentity.of(data) != asset.identity:
            raise ReferenceError('Reference asset integrity mismatch: '+self.reference.reference_id+':'+role)
        if inputs is not None:
            receipt=UsedInputReceipt.for_payload(SourcePayload(data,asset.media_type,self.reference.reference_id+':'+role),role)
            inputs.append(replace(receipt,content_basis=self.snapshot_identity))
        return data

    def validate_all(self):
        for asset in self.reference.assets:
            if asset.required:
                self.read(asset.role)


@dataclass(frozen=True, slots=True)
class ReferenceUse:
    reference_id: str
    role: str
    identity: ByteIdentity
    snapshot_identity: ByteIdentity

    def manifest_entry(self):
        return {'reference_id':self.reference_id,'role':self.role,
                'byte_identity':{'sha256':self.identity.sha256,'size':self.identity.size},
                'snapshot_identity':{'sha256':self.snapshot_identity.sha256,'size':self.snapshot_identity.size}}


def qualified_reference_use(inputs, *, package, role):
    selected=load_reference(package)
    reference_id=selected.reference.reference_id
    relevant=[item for item in inputs if item.source_id == reference_id+':'+role]
    if len(relevant)!=1:
        raise ReferenceError('Expected exactly one qualified reference use: '+reference_id+':'+role)
    receipt=relevant[0];asset=selected.asset(role)
    if (receipt.role!=role or receipt.identity!=asset.identity or receipt.content_basis!=selected.snapshot_identity
        or receipt.media_type!=asset.media_type or receipt.availability!='inline'):
        raise ReferenceError('Unqualified reference receipt: '+reference_id+':'+role)
    selected.read(role)
    return ReferenceUse(reference_id,role,asset.identity,selected.snapshot_identity)


REFERENCE_REQUIRED_ROLES={
    'banks':frozenset({'official_xlsx','aliases','default_selection','legacy_selection'}),
    'okved2':frozenset({'data','meta','structure'}),
    'geography':frozenset({'aliases'}),
}
_REFERENCE_IDENTITIES={'banks':'reference.banks','okved2':'reference.okved2','geography':'reference.geography.names'}
_ROLE=re.compile(r'[a-z][a-z0-9_]*\Z')
_MEDIA=re.compile(r'[a-z0-9!#$&^_.+-]+/[a-z0-9!#$&^_.+-]+\Z',re.ASCII)
_ORIGINS={'published_source','curated_policy','unknown'}


def _safe_path(value):
    if not isinstance(value,str) or not value or '\\' in value or value.startswith('/'):
        raise ReferenceError('Invalid reference asset path')
    path=PurePosixPath(value)
    if str(path)!=value or any(part in {'.','..',''} for part in path.parts):
        raise ReferenceError('Reference asset path escapes package root')
    return value


def _text(value,name):
    if value is not None and (not isinstance(value,str) or not value.strip()):
        raise ReferenceError('Invalid reference '+name)
    return value


def _date(value,name):
    if value is None:return None
    if not isinstance(value,str):raise ReferenceError('Invalid reference date '+name)
    try:return date.fromisoformat(value)
    except ValueError as error:raise ReferenceError('Invalid reference date '+name) from error


def parse_reference_manifest(package, document):
    prefix='stratbox.shared.reference.'
    family=package.removeprefix(prefix) if isinstance(package,str) and package.startswith(prefix) else ''
    if family not in REFERENCE_REQUIRED_ROLES:
        raise ReferenceError('Reference package must have an owned role contract')
    try:
        document=json.loads(document) if isinstance(document,bytes) else document
        if not isinstance(document,Mapping) or document.get('reference_id')!=_REFERENCE_IDENTITIES[family]:
            raise ReferenceError('Invalid reference identity')
        if set(document)&{'manifest_schema_version','active_edition','editions'}:
            raise ReferenceError('Reference contents have no independent release lifecycle')
        declared=document['assets']
        if not isinstance(declared,list) or not declared:raise ReferenceError('Reference assets required')
        assets=[];roles=set();paths=set()
        for item in declared:
            role=item['role'];path=_safe_path(item['path'])
            if not isinstance(role,str) or not _ROLE.fullmatch(role) or role in roles or path in paths:
                raise ReferenceError('Duplicate or invalid reference asset role/path')
            roles.add(role);paths.add(path)
            required=item.get('required',True);size=item['size'];media=item['media_type']
            if type(required) is not bool or type(size) is not int or size<0:
                raise ReferenceError('Invalid reference asset size/required flag')
            if not isinstance(media,str) or not _MEDIA.fullmatch(media):raise ReferenceError('Invalid media type')
            origin=_text(item.get('origin_kind'),'origin_kind')
            if origin is not None and origin not in _ORIGINS:raise ReferenceError('Unknown origin kind')
            assets.append(ReferenceAsset(role,package,path,media,ByteIdentity(item['sha256'],size),required,
                _text(item.get('publisher'),'publisher'),_text(item.get('curator'),'curator'),
                _text(item.get('source_url'),'source_url'),origin))
        if not REFERENCE_REQUIRED_ROLES[family]<=roles:raise ReferenceError('Incomplete reference roles: '+family)
        start=_date(document.get('effective_from'),'effective_from');end=_date(document.get('effective_to'),'effective_to')
        if start and end and start>end:raise ReferenceError('Inverted reference validity interval')
        return ReferenceDefinition(document['reference_id'],tuple(assets),
            _text(document.get('publisher'),'publisher'),_text(document.get('source_url'),'source_url'),
            _text(document.get('curator'),'curator'),_date(document.get('published_at'),'published_at'),start,end)
    except (ValueError,TypeError,KeyError,AttributeError,UnicodeError) as error:
        if isinstance(error,ReferenceError):raise
        raise ReferenceError('Malformed reference manifest: '+str(package)) from error


def load_reference(package):
    prefix='stratbox.shared.reference.'
    if not isinstance(package,str) or not package.startswith(prefix) or package[len(prefix):] not in REFERENCE_REQUIRED_ROLES:
        raise ReferenceError('Reference package must be an owned reference package')
    try:raw=resources.files(package).joinpath('_resources','manifest.json').read_bytes()
    except (FileNotFoundError,ModuleNotFoundError) as error:raise ReferenceError('Missing reference manifest: '+str(package)) from error
    reference=parse_reference_manifest(package,raw)
    manifest={'reference_id':reference.reference_id,'publisher':reference.publisher,'curator':reference.curator,
        'source_url':reference.source_url,'published_at':reference.published_at,
        'effective_from':reference.effective_from,'effective_to':reference.effective_to,
        'assets':[{'role':a.role,'path':a.path,'media_type':a.media_type,'sha256':a.identity.sha256,
            'size':a.identity.size,'required':a.required,'publisher':a.publisher,'curator':a.curator,
            'source_url':a.source_url,'origin_kind':a.origin_kind} for a in sorted(reference.assets,key=lambda a:(a.role,a.path))]}
    return LoadedReference(reference,ByteIdentity.of(canonical_manifest_bytes(manifest)))
