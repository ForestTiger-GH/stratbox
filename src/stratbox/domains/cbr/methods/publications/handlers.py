"""Thin registered publication operations over publisher-owned behavior."""
from stratbox.core.execution import OperationFailure
from stratbox.core.operations.source.validation import use_payload
from stratbox.domains.cbr.publications.catalog import all_sources
from stratbox.domains.cbr.publications.discovery import discover_value
from stratbox.domains.cbr.publications.admission import identify_value
from stratbox.domains.cbr.operations.publications import definitions as D

def list_sources(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('list_sources')
        try:
            return all_sources(req.family_id)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
    return work(request, invocation)

def discover(request, *, transport=None, selection=None, invocation=None):
    return (lambda req, invocation: discover_value(req, invocation, transport=transport))(request, invocation)

def identify(request, *, invocation=None):

    def work(req, invocation):
        invocation.stage('identify')
        use_payload(req.payload, invocation, role='supplied_material', limit=256 * 1024 ** 2)
        value = identify_value(req, invocation)
        invocation.account_output(value.payload.identity)
        return value
    return work(request, invocation)

def select(request, *, invocation=None):
    from stratbox.domains.cbr.publications.selection import select_publication

    def work(req, invocation):
        invocation.stage('select')
        try:
            return select_publication(req)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
    return work(request, invocation)

def acquire(request, *, transport=None, selection=None, invocation=None):
    from stratbox.domains.cbr.publications.acquisition import acquire_publication

    def work(req, invocation):
        invocation.stage('acquire')
        try:
            return acquire_publication(req, invocation, transport=transport)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
    return work(request, invocation)

def assess_updates(request, *, invocation=None):
    from stratbox.domains.cbr.publications.updates import assess_updates as assess_value

    def work(req, invocation):
        invocation.stage('assess_updates')
        try:
            return assess_value(req)
        except ValueError as error:
            raise OperationFailure(str(error)) from None
    return work(request, invocation)


def capability_acquire(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.publications.acquire', acquire)


def capability_assess_updates(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.publications.assess_updates', assess_updates)


def capability_discover(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.publications.discover', discover)


def capability_identify(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.publications.identify', identify)


def capability_list_sources(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.publications.list_sources', list_sources)


def capability_select(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.publications.select', select)
