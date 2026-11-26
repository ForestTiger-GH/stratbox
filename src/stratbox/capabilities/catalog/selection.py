"""Pure source discovery and exact caller selection over static domain records."""
from dataclasses import replace

from stratbox.shared.data.selection import SourceSelection, SelectionError, source_query
from stratbox.shared.data.values import fingerprint
from ..model.domains import PublicationDescriptor, PublicationSpec


def source_records(catalog, *, domain_id=None, include_feeds=True):
    if domain_id is not None and domain_id not in catalog.domains:
        raise SelectionError('selection.unknown_domain')
    result = {}
    for key, domain in catalog.domains.items():
        if domain_id is not None and key != domain_id:
            continue
        for source_id, record in domain.series.items():
            result[source_id] = ('series', record)
        if include_feeds:
            for source_id, record in domain.common.get('publications', {}).items():
                result[source_id] = ('feed', record)
    return result


def publication_descriptor(record, *, kind='series'):
    publication = record if isinstance(record, PublicationSpec) else record.publication
    descriptor = getattr(publication, 'descriptor', None)
    if not isinstance(descriptor, PublicationDescriptor):
        raise SelectionError('selection.publication_descriptor_required:' + record.id)
    return replace(descriptor, source_id=record.id, target_kind=kind,
        stage_support=tuple(sorted(set(descriptor.stage_support) | set(record.commands))))


def resolve_sources(catalog, query):
    query = source_query(query)
    records = source_records(catalog)
    descriptors = {key: publication_descriptor(record, kind=kind) for key, (kind, record) in records.items()}
    explicit = set(query.includes) | set(query.excludes) | set(query.order)
    if explicit - descriptors.keys():
        raise SelectionError('selection.unknown_source:' + sorted(explicit - descriptors.keys())[0])
    matches = set()
    if query.mode in {'predicate', 'all'}:
        for key, descriptor in descriptors.items():
            if all((bool(set(getattr(descriptor, field)) & set(values))
                    if isinstance(getattr(descriptor, field), (tuple, frozenset))
                    else getattr(descriptor, field) in values) for field, values in query.facets.items()):
                matches.add(key)
    matches.update(query.includes)
    excluded = tuple(sorted(matches & set(query.excludes)))
    matches.difference_update(query.excludes)
    if set(query.order) - matches:
        raise SelectionError('selection.order_outside_selected_scope')
    order = tuple(dict.fromkeys((*query.order, *(key for key in query.includes if key in matches))))
    selected = (*order, *sorted(matches - set(order)))
    if len(selected) > query.max_items:
        raise SelectionError('selection.source_limit')
    basis = fingerprint(tuple(descriptors[key] for key in sorted(descriptors)))
    return SourceSelection(query, basis, tuple(selected), excluded)
