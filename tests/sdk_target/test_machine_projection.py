from dataclasses import dataclass
from decimal import Decimal
from types import MappingProxyType
import pytest
from stratbox.sdk.machine import project, invoke


def test_projection_preserves_exact_decimals_and_bounds_nested_values():
    result=project({'amount':Decimal('1.000000000000000001'),'data':b'abc','items':tuple(range(100))},max_items=8)
    assert result['amount']=={'decimal':'1.000000000000000001'}
    assert result['data']['size']==3 and 'abc' not in str(result['data'])
    assert len(result['items'])<100


def test_projection_handles_immutable_dataclass_without_deepcopy():
    @dataclass(frozen=True)
    class Value:
        rows: object
    assert project(Value(MappingProxyType({'x':Decimal('2')})))=={'rows':{'x':{'decimal':'2'}}}


def test_machine_request_rejects_unrecognized_control_fields():
    with pytest.raises(ValueError,match='unknown_request_fields'):
        invoke(object(),{'capability_id':'command.material.read','handler':'arbitrary'})
