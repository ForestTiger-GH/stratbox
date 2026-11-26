"""Journal pages are portable pure records with immutable observation metadata."""
import pytest

from stratbox.core.observability.journal import MemoryJournal
from stratbox.shared.data.values import canonical_tree, fingerprint, restore_tree, validate_portable_tree


def test_page_and_checkpoint_roundtrip_with_exact_content_identity():
    journal = MemoryJournal()
    journal.append(kind='output.accepted', run_id='first', data={'details': {'count': [1, 2]}})
    journal.append(kind='run.finished', run_id='other')
    for value in (journal.read_page(), journal.read_page(run_id='first'), journal.checkpoint()):
        tree = validate_portable_tree(canonical_tree(value))
        restored = restore_tree(tree)
        assert type(restored) is type(value)
        assert fingerprint(restored) == fingerprint(value)
    page = restore_tree(canonical_tree(journal.read_page()))
    with pytest.raises(TypeError):
        page.facts[0].data['details']['count'] = (3,)
