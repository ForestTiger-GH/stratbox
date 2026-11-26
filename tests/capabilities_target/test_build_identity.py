"""Direct preparation and SDK invocation pin the same packaged rules and code."""
from stratbox.capabilities.preparation import prepare
from stratbox.sdk import StrategyBox
from stratbox.shared.build import implementation_identity


def test_direct_and_sdk_preparation_use_one_implementation_basis():
    direct = prepare('command.value.encode', inputs={'value': 7})
    with StrategyBox() as box:
        facade = box.prepare('command.value.encode', inputs={'value': 7})
    assert direct.build_identity == facade.build_identity == implementation_identity()
    assert direct.fingerprint == facade.fingerprint


def test_rule_content_changes_the_basis_without_component_versions(tmp_path, monkeypatch):
    from stratbox.shared import build
    package = tmp_path / 'stratbox'
    package.mkdir()
    (package / '__init__.py').write_text('value = 1\n')
    rule = package / 'rules.json'
    rule.write_text('{"scale":1}')
    monkeypatch.setattr(build.resources, 'files', lambda name: package)
    first = implementation_identity()
    rule.write_text('{"scale":1000}')
    assert implementation_identity() != first
    changed = implementation_identity()
    (package / 'README.md').write_text('Navigation only.\n')
    assert implementation_identity() == changed
