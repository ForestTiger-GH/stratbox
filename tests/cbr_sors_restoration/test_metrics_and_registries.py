from stratbox.macrobanks.cbr_sors_restoration.metrics import source_metric
from stratbox.macrobanks.cbr_sors_restoration.registries.okved2 import read_okved2_classes
from stratbox.macrobanks.cbr_sors_restoration.registries.publication_categories import (
    PUBLISHED_OTHER_CLASSES,
    enrich_okved2_classes,
    build_publication_categories,
)


def test_metrics_cover_all_six_publications() -> None:
    assert source_metric('debt', 'rub') == 'debt_rub'
    assert source_metric('debt', 'fx') == 'debt_fx'
    assert source_metric('debt', 'total') == 'debt_total'
    assert source_metric('overdue', 'rub') == 'overdue_rub'
    assert source_metric('overdue', 'fx') == 'overdue_fx'
    assert source_metric('overdue', 'total') == 'overdue_total'


def test_okved2_registry_has_atomic_and_publication_layers() -> None:
    classes = read_okved2_classes()
    assert len(classes) == 88
    assert classes.loc[classes['section_code'].eq('C'), 'section_name'].iloc[0] == 'Обрабатывающие производства'
    enriched = enrich_okved2_classes(classes, build_publication_categories(classes))
    other = enriched[enriched['class_code'].isin(PUBLISHED_OTHER_CLASSES)]
    assert set(other['class_code']) == set(PUBLISHED_OTHER_CLASSES)
    assert not other['is_individually_published'].any()
    assert set(other['publication_category_code']) == {'PUBLISHED_OTHER'}
