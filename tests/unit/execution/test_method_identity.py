"""A method fingerprints its meaning and reachable executable dependencies."""
from dataclasses import replace

import pytest

from stratbox.core.execution import OperationDefinition
from stratbox.core.execution import methods
from stratbox.shared.data.datasets import computation_identity


def definition():
    return OperationDefinition("fixture.calculate", "calculate", int, int,
        method_refs=("stratbox.fixture:calculate",))


def sources(monkeypatch):
    contents = {
        "stratbox.fixture": b'from stratbox.formulas import formula\ndef calculate(value):\n    """Calculate a value."""\n    return formula(value)\ndef unrelated(value):\n    return 0\n',
        "stratbox.formulas": b'def formula(value):\n    return value * 2\n',
    }
    monkeypatch.setattr(methods, "_source", lambda module: (contents[module], False))
    return contents


def test_formula_helper_changes_method_but_editorial_or_unrelated_changes_do_not(monkeypatch):
    contents = sources(monkeypatch)
    before = methods.method_descriptor(definition())
    contents["stratbox.fixture"] = contents["stratbox.fixture"].replace(b"Calculate a value.", b"Different documentation.").replace(b"return 0", b"return 999") + b"\n# Editorial clarification\n"
    assert before.identity == methods.method_descriptor(definition()).identity
    contents["stratbox.formulas"] = b'def formula(value):\n    return value * 3\n'
    after = methods.method_descriptor(definition())
    assert before.identity != after.identity
    assert computation_identity("fixture.calculate", "calculate", (), method_fingerprint=before.identity) != (
        computation_identity("fixture.calculate", "calculate", (), method_fingerprint=after.identity))
    assert {name for name, _ in after.algorithms} == {
        "stratbox.fixture:calculate", "stratbox.formulas:formula"}


def test_missing_explicit_algorithm_is_admission_failure(monkeypatch):
    sources(monkeypatch)
    with pytest.raises(methods.MethodError, match="method.reference_unavailable"):
        methods.method_descriptor(replace(definition(), method_refs=("stratbox.fixture:missing",)))


@pytest.mark.parametrize("statement", [
    "from stratbox import formulas", "import stratbox.formulas as formulas",
    "import stratbox.formulas",
])
def test_transitive_module_aliases_preserve_substantive_helper_dependencies(monkeypatch, statement):
    contents = sources(monkeypatch)
    contents["stratbox"] = b""
    call = "stratbox.formulas.formula(value)" if statement == "import stratbox.formulas" else "formulas.formula(value)"
    contents["stratbox.fixture"] = (statement + "\ndef calculate(value):\n    return " + call + "\n").encode()
    before = methods.method_descriptor(definition())
    contents["stratbox.formulas"] = b"def formula(value):\n    return value * 3\n"
    assert before.identity != methods.method_descriptor(definition()).identity


def test_profile_resource_contents_participate_without_package_release_numbers(monkeypatch, tmp_path):
    sources(monkeypatch)
    resource = tmp_path / "rules" / "_resources" / "profile.json"
    resource.parent.mkdir(parents=True)
    resource.write_text('{"rounding":"exact"}')
    monkeypatch.setattr(methods, "files", lambda package: tmp_path)
    operation = replace(definition(), method_resources=("stratbox.rules:_resources/profile.json",))
    before = methods.method_descriptor(operation)
    resource.write_text('{"rounding":"published"}')
    assert before.identity != methods.method_descriptor(operation).identity


def test_inline_lambda_fingerprint_ignores_the_surrounding_callsite():
    first = lambda value, invocation: value * 2
    second = lambda value, invocation: value * 2
    assert methods.callable_fingerprint(first) == methods.callable_fingerprint(second)
