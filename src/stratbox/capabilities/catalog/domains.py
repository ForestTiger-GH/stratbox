"""Fixed domain manifest and direct record lookup without contribution assembly."""
from dataclasses import dataclass
from collections.abc import Mapping
from importlib import import_module
from ..model import DomainSpec, PublicationSpec, freeze

DOMAINS = freeze({
    'cbr': 'stratbox.domains.cbr.domain:DOMAIN',
    'fns': 'stratbox.domains.fns.domain:DOMAIN',
    'minfin': 'stratbox.domains.minfin.domain:DOMAIN',
    'frank_rg': 'stratbox.domains.frank_rg.domain:DOMAIN',
    'rosstat': 'stratbox.domains.rosstat.domain:DOMAIN',
})

@dataclass(frozen=True)
class DomainCatalog:
    domains: Mapping[str, DomainSpec]

    def __post_init__(self):
        object.__setattr__(self, 'domains', freeze(self.domains))
        if any(not isinstance(v, DomainSpec) or key != v.id for key, v in self.domains.items()):
            raise ValueError('catalog.domain_identity')
        seen = set()
        for domain in self.domains.values():
            publications = domain.common.get('publications', {})
            if (not isinstance(publications, Mapping) or any(not isinstance(value, PublicationSpec) or key != value.id
                    for key, value in publications.items())):
                raise ValueError('catalog.feed_identity')
            for group in (domain.series, domain.calculations, domain.products, publications):
                for key in group:
                    if key in seen: raise ValueError('catalog.duplicate_target:' + key)
                    seen.add(key)

    def get(self, identifier, *, kind=None):
        matches = []
        for domain in self.domains.values():
            groups={'series':domain.series, 'calculation':domain.calculations, 'product':domain.products}
            for name, group in groups.items():
                if kind is not None and kind != name: continue
                if identifier in group: matches.append(group[identifier])
            publications = domain.common.get('publications', {})
            if isinstance(publications, Mapping) and identifier in publications and kind in {None, 'feed'}:
                matches.append(publications[identifier])
        if len(matches) != 1: raise ValueError('catalog.target_' + ('unknown' if not matches else 'ambiguous') + ':' + identifier)
        return matches[0]


def load_domains(ids=None):
    selected = tuple(DOMAINS) if ids is None else tuple(ids)
    values = {}
    for name in selected:
        if name not in DOMAINS: raise ValueError('catalog.unknown_domain:' + name)
        module, attr = DOMAINS[name].split(':')
        values[name] = getattr(import_module(module), attr)
    return DomainCatalog(values)
