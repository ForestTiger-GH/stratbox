"""Thin registered publication operations over publisher-owned behavior."""
from stratbox.core.execution import OperationFailure, run
from stratbox.core.operations.source.validation import use_payload
from stratbox.domains.cbr.publications.catalog import all_sources
from stratbox.domains.cbr.publications.discovery import discover_value
from stratbox.domains.cbr.publications.admission import identify_value
from . import definitions as D


def list_sources(request, *, context=None):
    def work(req, invocation):
        invocation.stage("list_sources")
        try:
            return all_sources(req.family_id)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
    return run(D.LIST, request, work, context=context)


def discover(request, *, transport=None, selection=None, context=None):
    return run(D.DISCOVER, request,
        lambda req, invocation: discover_value(req, invocation, transport=transport),
        context=context, providers={"http": transport},
        provider_selections={"http": selection} if selection is not None else None)


def identify(request, *, context=None):
    def work(req, invocation):
        invocation.stage("identify")
        use_payload(req.payload, invocation, role="supplied_material", limit=256 * 1024**2)
        value = identify_value(req, invocation)
        invocation.account_output(value.payload.identity)
        return value
    return run(D.IDENTIFY, request, work, context=context)


def select(request, *, context=None):
    from stratbox.domains.cbr.publications.selection import select_publication
    def work(req, invocation):
        invocation.stage("select")
        try:
            return select_publication(req)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
    return run(D.SELECT, request, work, context=context)


def acquire(request, *, transport=None, selection=None, context=None):
    from stratbox.domains.cbr.publications.acquisition import acquire_publication
    def work(req, invocation):
        invocation.stage("acquire")
        try:
            return acquire_publication(req, invocation, transport=transport)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
    return run(D.ACQUIRE, request, work, context=context, providers={"http": transport},
               provider_selections={"http": selection} if selection is not None else None)


def assess_updates(request, *, context=None):
    from stratbox.domains.cbr.publications.updates import assess_updates as assess_value
    def work(req, invocation):
        invocation.stage("assess_updates")
        try:
            return assess_value(req)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
    return run(D.ASSESS_UPDATES, request, work, context=context)
