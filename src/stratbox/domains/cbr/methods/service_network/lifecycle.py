"""Independently callable service-network lifecycle boundaries."""
from dataclasses import asdict
from stratbox.core.execution import OperationFailure
from stratbox.shared.identity import ByteIdentity, canonical_manifest_bytes
from stratbox.shared.evidence import UsedInputReceipt
from stratbox.domains.cbr.operations.service_network.lifecycle_definitions import READABLE, HISTORY, RESTORE_HISTORY, ALIGN, CHANGES, VIEW, RENDER

def _call(definition, request, action, invocation):

    def work(req, invocation):
        try:
            return action(req, invocation)
        except (ValueError, TypeError, KeyError) as error:
            text = str(error)
            raise OperationFailure(text if text.startswith(('cbr.', 'request.', 'source.')) else 'source.office_lifecycle_invalid') from None
    return work(request, invocation)

def make_readable(request, *, invocation=None):
    from stratbox.domains.cbr.tables.service_network.readable import readable
    return _call(READABLE, request, readable, invocation)

def build_source_history(request, *, invocation=None):
    from stratbox.domains.cbr.tables.service_network.history import build_history

    def work(req, invocation):
        invocation.stage('source_history')
        result = build_history(req)
        for receipt in result.manifest.inputs:
            invocation.use(receipt)
        invocation.record(result.identity)
        return result
    return _call(HISTORY, request, work, invocation)

def restore_history(request, *, invocation=None):
    from stratbox.domains.cbr.tables.service_network.history import restore_history as decode

    def work(req, invocation):
        invocation.stage('restore_history')
        invocation.use(UsedInputReceipt('retained_history', req.identity, 'application/vnd.stratbox.dataset+json', 'inline', req.manifest.dataset_id))
        for receipt in req.manifest.inputs:
            invocation.use(receipt)
        return decode(req)
    return _call(RESTORE_HISTORY, request, work, invocation)

def align_offices(request, *, invocation=None):
    from stratbox.domains.cbr.integration.service_network.alignment import align
    return _call(ALIGN, request, align, invocation)

def calculate_changes(request, *, invocation=None):
    from stratbox.domains.cbr.analytics.service_network.changes import calculate

    def work(req, invocation):
        invocation.stage('calculate_count_changes')
        result = calculate(req)
        for receipt in result.batch.lineage:
            invocation.use(receipt)
        invocation.record(ByteIdentity.of(canonical_manifest_bytes(asdict(result))))
        return result
    return _call(CHANGES, request, work, invocation)

def build_view(request, *, invocation=None):
    from stratbox.domains.cbr.products.service_network.views import build_view as prepare

    def work(req, invocation):
        invocation.stage('prepare_view')
        result = prepare(req)
        for receipt in result.manifest.inputs:
            invocation.use(receipt)
        invocation.record(result.identity)
        return result
    return _call(VIEW, request, work, invocation)

def render(request, *, invocation=None):
    from stratbox.domains.cbr.products.service_network.views import render_view

    def work(req, invocation):
        invocation.stage('render')
        invocation.use(UsedInputReceipt('prepared_office_view', req.view.identity, 'application/vnd.stratbox.dataset+json', 'inline', req.view.manifest.dataset_id))
        return render_view(req, invocation.budget)
    return _call(RENDER, request, work, invocation)


def capability_align_offices(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.service_network.align', align_offices)


def capability_build_source_history(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.service_network.build_history', build_source_history)


def capability_build_view(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.service_network.build_view', build_view)


def capability_calculate_changes(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.service_network.calculate_changes', calculate_changes)


def capability_make_readable(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.service_network.make_readable', make_readable)


def capability_render(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.service_network.render', render)


def capability_restore_history(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.service_network.restore_history', restore_history)
