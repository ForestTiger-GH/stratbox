"""One discovery, preparation and execution path for every callable kind."""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class CatalogPage:
    entries: tuple[object, ...]
    offset: int
    total: int
    next_offset: int | None


class SourceAPI:
    """Bounded discovery and caller-owned selection of declared publications."""
    def __init__(self, box):
        self._box = box

    def source(self, series_id):
        from stratbox.capabilities.catalog.selection import source_records
        try:
            return source_records(self._box.domains)[series_id][1]
        except KeyError:
            raise KeyError('source.unknown_or_ambiguous:' + str(series_id)) from None

    def list(self, *, domain_id=None, query=None, offset=0, limit=200, include_feeds=False):
        return self.page(domain_id=domain_id, query=query, offset=offset, limit=limit,
                         include_feeds=include_feeds).entries

    def page(self, *, domain_id=None, query=None, offset=0, limit=100, include_feeds=False):
        from stratbox.capabilities.catalog.selection import source_records
        from stratbox.shared.data.selection import SourceQuery
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError('sdk.page_invalid')
        records = source_records(self._box.domains, domain_id=domain_id, include_feeds=include_feeds)
        if isinstance(query, (SourceQuery, Mapping)):
            selected = self.select(query).source_ids
            values = [records[key][1] for key in selected if key in records]
        elif query is None or isinstance(query, str):
            values = [record for key, (_, record) in sorted(records.items())
                      if query is None or query.casefold() in key.casefold()]
        else:
            raise TypeError('sdk.query_invalid')
        stop = min(offset + limit, len(values))
        return CatalogPage(tuple(values[offset:stop]), offset, len(values), stop if stop < len(values) else None)

    def select(self, query):
        from stratbox.capabilities.catalog.selection import resolve_sources
        return resolve_sources(self._box.domains, query)

    def descriptor(self, source_id):
        from stratbox.capabilities.catalog.selection import source_records, publication_descriptor
        kind, record = source_records(self._box.domains)[source_id]
        return publication_descriptor(record, kind=kind)

    def describe(self, series_id):
        from .machine import project
        result = project(self.source(series_id), max_items=200)
        result['descriptor'] = project(self.descriptor(series_id), max_items=200)
        return result


class StrategyBox:
    """Own one bounded multicall service with lazy providers and backend imports."""
    def __init__(self, *, settings=None, providers=None, catalog=None, domains=None,
                 observer=None, journal=None, build_identity=None, admission_guard=None):
        from .bootstrap import default_catalog
        self.catalog = catalog if catalog is not None else default_catalog()
        self._domains = domains
        self.settings = settings
        self.providers = dict(providers or {})
        self.observer = observer
        self.journal = journal
        self.admission_guard = admission_guard
        self._build_identity = build_identity
        self._session = None
        self._closed = False
        self._lock = RLock()
        self.sources = SourceAPI(self)

    def _check_open(self):
        if self._closed:
            raise RuntimeError('sdk.closed')

    @property
    def domains(self):
        with self._lock:
            self._check_open()
            if self._domains is None:
                from .bootstrap import default_domains
                self._domains = default_domains()
            return self._domains

    @property
    def session(self):
        with self._lock:
            self._check_open()
            if self._session is None:
                from stratbox.core.execution.service import ExecutionService
                self._session = ExecutionService(providers=self.providers, settings=self.settings,
                                                 observer=self.observer, journal=self.journal,
                                                 admission_guard=self.admission_guard)
            return self._session

    def prepare(self, capability, *, inputs=None, parameters=None, target=None, outputs=None):
        from stratbox.capabilities.preparation import prepare
        from stratbox.capabilities.model.definitions import CapabilityDefinition
        with self._lock:
            self._check_open()
            catalog = self.catalog
            if isinstance(capability, CapabilityDefinition):
                catalog = catalog.with_definitions(capability)
                identifier = capability.id
            elif isinstance(capability, str):
                identifier = capability
            else:
                raise TypeError('sdk.capability_required')
            if self._build_identity is None:
                from .bootstrap import implementation_identity
                self._build_identity = implementation_identity()
            return prepare(identifier, inputs=inputs, parameters=parameters, target=target,
                           outputs=tuple(outputs) if outputs is not None else None,
                           catalog=catalog, domains=self.domains, build_identity=self._build_identity)

    def invoke(self, capability, *, inputs=None, parameters=None, target=None, outputs=None, timeout=None):
        plan = self.prepare(capability, inputs=inputs, parameters=parameters, target=target, outputs=outputs)
        return self.session.run(plan, timeout=timeout)

    def preflight(self, capability, *, inputs=None, parameters=None, target=None, outputs=None, resolve_methods=True):
        """Inspect a selected request without network access or external mutation."""
        self._check_open()
        from .readiness import preflight
        return preflight(self, capability, inputs=inputs, parameters=parameters, target=target,
                         outputs=outputs, resolve_methods=resolve_methods)

    def export_recovery(self, destination, *, timeout=60, limits=None, retained_references=()):
        self._check_open()
        from stratbox.core.recovery import export_recovery_package
        return export_recovery_package(self, destination, timeout=timeout, limits=limits,
                                       retained_references=retained_references)

    def processing_basis(self, capability, *, inputs=None, parameters=None, target=None):
        """Compare a direct command's desired work without executing it.

        Pass ``fingerprint(result)`` as a ProcessingRequirement basis identity.
        Operation inputs contain unresolved intermediate values, so they need
        the basis of their actual finite command stage instead.
        """
        from stratbox.capabilities.plan.models import CommandTask
        from stratbox.shared.data.processing import processing_basis
        plan = self.prepare(capability, inputs=inputs, parameters=parameters, target=target)
        if (not plan.scopes or plan.scopes[0].kind != 'command' or len(plan.tasks) != 1
                or not isinstance(plan.tasks[0], CommandTask)):
            raise ValueError('processing.direct_command_required')
        task = plan.tasks[0]
        command = task.command
        return processing_basis(task.inputs, capability_id=command.id, method=command.method,
            settings=command.settings, parameters=command.parameters, build_identity=plan.build_identity)

    def run(self, plan, *, timeout=None):
        self._check_open()
        return self.session.run(plan, timeout=timeout)

    def submit(self, capability_or_plan, *, inputs=None, parameters=None, target=None, outputs=None, timeout=None):
        from stratbox.capabilities.plan import PreparedPlan
        if isinstance(capability_or_plan, PreparedPlan):
            if any(value is not None for value in (inputs, parameters, target, outputs)):
                raise ValueError('sdk.prepared_plan_arguments')
            plan = capability_or_plan
        else:
            plan = self.prepare(capability_or_plan, inputs=inputs, parameters=parameters, target=target, outputs=outputs)
        return self.session.submit(plan, timeout=timeout)

    def advance_source_state(self, *, max_pages=10, page_limit=1000, consumer_id='source-state'):
        """Replay a bounded journal slice before requesting a fresh state view."""
        from stratbox.core.observability.projections import SourceStateIndex
        session = self.session
        store = session.resolve_provider('source_state')
        return SourceStateIndex(store,consumer_id=consumer_id).advance(
            session.journal,max_pages=max_pages,page_limit=page_limit)

    def describe(self, capability_id):
        self._check_open()
        from .machine import project
        try:
            definition = self.catalog.definitions[capability_id]
        except KeyError:
            raise KeyError('capability.unknown:' + str(capability_id)) from None
        result = project(definition, max_items=200)
        result['kind'] = definition.kind
        return result

    def discover(self, *, kind=None, query=None, offset=0, limit=100):
        self._check_open()
        if kind not in {None, 'command', 'operation', 'scenario', 'cascade'}:
            raise ValueError('sdk.kind_invalid')
        if type(offset) is not int or offset < 0 or type(limit) is not int or not 1 <= limit <= 200:
            raise ValueError('sdk.page_invalid')
        if query is not None and not isinstance(query, str):
            raise TypeError('sdk.query_invalid')
        selected = [definition for _, definition in sorted(self.catalog.definitions.items())
                    if (kind is None or definition.kind == kind)
                    and (query is None or query.casefold() in (definition.id + ' ' + definition.summary).casefold())]
        stop = min(offset + limit, len(selected))
        return CatalogPage(tuple(self.describe(value.id) for value in selected[offset:stop]),
                           offset, len(selected), stop if stop < len(selected) else None)

    def close(self, *, wait=True, cancel=False):
        with self._lock:
            self._closed = True
            service = self._session
        if service is not None:
            service.close(wait=wait, cancel=cancel)

    def __enter__(self):
        self._check_open()
        return self

    def __exit__(self, *exc):
        self.close()
