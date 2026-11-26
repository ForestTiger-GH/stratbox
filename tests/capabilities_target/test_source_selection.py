"""Caller membership, catalog consistency and bounded source discovery."""
from dataclasses import replace
from types import SimpleNamespace

import pytest

from stratbox.capabilities.catalog.domains import DomainCatalog
from stratbox.capabilities.catalog.selection import resolve_sources
from stratbox.capabilities.model import DomainSpec, SeriesSpec, PublicationSpec
from stratbox.sdk.client import SourceAPI
from stratbox.shared.data.selection import SourceQuery


def catalog(extra=False):
    publications = [PublicationSpec('p.fixed', formats={'xlsx'}, issue_model='rolling', delivery_mode='fixed_url'),
                    PublicationSpec('p.monthly', formats={'xlsx'}, issue_model='dated')]
    if extra:
        publications.append(PublicationSpec('p.new', formats={'xlsx'}, issue_model='rolling', delivery_mode='fixed_url'))
    series = {p.id: SeriesSpec(p.id, p, {}, {}) for p in publications}
    return DomainCatalog({'p': DomainSpec('p', {}, series)})


def test_predicate_is_caller_owned_and_resolved_membership_is_frozen():
    query = SourceQuery('predicate', facets={'issue_model': ('rolling',), 'formats': ('xlsx',)})
    selection = resolve_sources(catalog(), query)
    assert selection.source_ids == ('p.fixed',)
    refreshed = resolve_sources(catalog(True), query)
    assert refreshed.source_ids == ('p.fixed', 'p.new')
    assert selection.source_ids == ('p.fixed',)
    assert selection.declaration_basis != refreshed.declaration_basis


def test_exact_order_additions_exclusions_and_unknown_ids():
    query = SourceQuery('all', excludes=('p.monthly',), order=('p.fixed',))
    assert resolve_sources(catalog(), query).source_ids == ('p.fixed',)
    assert resolve_sources(catalog(), SourceQuery(includes=())).source_ids == ()
    with pytest.raises(ValueError, match='unknown_source'):
        resolve_sources(catalog(), SourceQuery(includes=('missing',)))
    with pytest.raises(ValueError, match='unknown_source'):
        resolve_sources(catalog(), SourceQuery(excludes=('missing',)))
    with pytest.raises(ValueError, match='unknown_source_facet'):
        SourceQuery('predicate', facets={'collector_preset': ('anything',)})
    with pytest.raises(ValueError, match='unknown_query_field'):
        resolve_sources(catalog(), {'mode': 'all', 'silently_select_all': True})


def test_feed_identity_and_cross_kind_collisions_are_rejected():
    original = catalog().domains['p']
    with pytest.raises(ValueError, match='duplicate_target'):
        DomainCatalog({'p': replace(original, common={'publications': {'p.fixed': PublicationSpec('p.fixed')}})})
    with pytest.raises(ValueError, match='feed_identity'):
        DomainCatalog({'p': replace(original, common={'publications': {'p.feed': PublicationSpec('p.other')}})})


def test_sdk_pages_are_bounded_and_descriptor_projects_known_facts():
    sources = SourceAPI(SimpleNamespace(domains=catalog()))
    page = sources.page(limit=1)
    assert len(page.entries) == 1 and page.total == 2 and page.next_offset == 1
    assert sources.page(offset=page.next_offset, limit=1).next_offset is None
    assert sources.descriptor('p.fixed').issue_model == 'rolling'
    assert sources.describe('p.fixed')['descriptor']['delivery_mode'] == 'fixed_url'
    assert sources.select(SourceQuery(includes=('p.monthly',))).source_ids == ('p.monthly',)
    with pytest.raises(ValueError, match='page_invalid'):
        sources.list(limit=1000000)
