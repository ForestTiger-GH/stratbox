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
    """Read-only access to the explicit continuing-series declarations."""
    def __init__(self, box):
        self._box = box

    def source(self, series_id):
        matches = [domain.series[series_id] for domain in self._box.domains.domains.values()
                   if series_id in domain.series]
        if len(matches) != 1:
            raise KeyError('source.unknown_or_ambiguous:' + str(series_id))
        return matches[0]

    def list(self, *, domain_id=None, query=None):
        values = []
        for key, domain in self._box.domains.domains.items():
            if domain_id is not None and key != domain_id:
                continue
            values.extend(series for series in domain.series.values()
                          if query is None or query.casefold() in series.id.casefold())
        return tuple(sorted(values, key=lambda value: value.id))

    def describe(self, series_id):
        from .machine import project
        return project(self.source(series_id), max_items=200)


class StrategyBox:
    """Own one bounded multicall service with lazy providers and backend imports."""
    def __init__(self, *, settings=None, providers=None, catalog=None, domains=None,
                 observer=None, journal=None, build_identity=None):
        from .bootstrap import default_catalog
        self.catalog = catalog if catalog is not None else default_catalog()
        self._domains = domains
        self.settings = settings
        self.providers = dict(providers or {})
        self.observer = observer
        self.journal = journal
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
                                                 observer=self.observer, journal=self.journal)
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
            if self._closed:
                return
            self._closed = True
            service = self._session
        if service is not None:
            service.close(wait=wait, cancel=cancel)

    def __enter__(self):
        self._check_open()
        return self

    def __exit__(self, *exc):
        self.close()
