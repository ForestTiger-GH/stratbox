from stratbox.macrobanks.cbr_sors_restoration.schema import (
    publication_interval,
    published_bucket,
    section_for_class,
)


def test_okved2_sections():
    assert section_for_class('01') == 'A'
    assert section_for_class('03') == 'A'
    assert section_for_class('35') == 'D'
    assert section_for_class('68') == 'L'
    assert section_for_class('85') == 'P'
    assert section_for_class('86') == 'OTHER'
    assert section_for_class('OTHER') == 'OTHER'


def test_publication_interval_zero_is_not_exact_zero():
    assert publication_interval(0.0) == (0.0, 0.5)
    assert published_bucket(0.0, 0.499999) == 0.0


def test_noncollapsed_interval_is_not_published_point():
    assert published_bucket(10.2, 11.2) is None
