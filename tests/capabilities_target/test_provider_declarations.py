"""Required and conditional provider dependencies have separate admission phases."""
from stratbox.capabilities.catalog import Catalog
from stratbox.capabilities.model import CommandDefinition, PortContract, MethodRef
from stratbox.capabilities.preparation import prepare
from stratbox.core.execution.service import ExecutionService

CALLS=[]


def dependency(inputs,settings,context):
    CALLS.append('entered')
    if context.parameters.get('use',False): context.provider('fixture_backend')
    return {'value':3}


def command(*,required=(),optional=(),use=False):
    return CommandDefinition('command.test.dependency',outputs={'value':PortContract('integer',int)},
        method=MethodRef(__name__+':dependency'),parameters={'use':use},
        required_providers=frozenset(required),optional_providers=frozenset(optional))


def run(definition,providers=None):
    with ExecutionService(providers=providers) as service:
        return service.run(prepare(definition.id,catalog=Catalog({definition.id:definition})),timeout=3)


def test_undeclared_provider_is_rejected_even_when_host_supplies_it():
    CALLS.clear()
    result=run(command(use=True),{'fixture_backend':object()})
    assert result.outcome=='failed'
    assert any('undeclared' in item for item in result.diagnostics)


def test_optional_provider_is_looked_up_only_when_method_requests_it():
    CALLS.clear()
    assert run(command(optional=('fixture_backend',))).outcome=='succeeded'
    missing=run(command(optional=('fixture_backend',),use=True))
    assert missing.outcome=='failed' and any('missing' in item for item in missing.diagnostics)
    assert run(command(optional=('fixture_backend',),use=True),{'fixture_backend':object()}).outcome=='succeeded'


def test_required_provider_missing_prevents_handler_admission():
    CALLS.clear()
    result=run(command(required=('fixture_backend',)))
    assert result.outcome=='failed' and not CALLS
