from datetime import datetime,timezone
from hashlib import sha256

from stratbox.sdk import StrategyBox
from stratbox.core.network import HttpResponse,HttpsRoute,RoutedTransport
from stratbox.shared.data.values import RequestSpec


class PeerTransport:
    def __init__(self,assurance='peer_bound'):
        self.calls=[]
        self.assurance=assurance
    def exchange(self,request,**options):
        self.calls.append(request)
        return HttpResponse(200,b'%PDF-1.7\noriginal',{'content-type':'application/pdf'},
            datetime(2026,11,23,tzinfo=timezone.utc),'https://gateway.example',self.assurance,
            sha256(request.url.encode()).hexdigest())


def test_routed_response_preserves_logical_and_actual_transport_evidence():
    route=HttpsRoute('published-reports',('publisher.example',),'https://gateway.example/public/')
    backend=PeerTransport()
    with StrategyBox(providers={'http':RoutedTransport(backend,(route,))}) as box:
        request=RequestSpec('https://publisher.example/reports/month.pdf',source_id='publisher.report')
        result=box.invoke('command.material.fetch',inputs={'request':request})
        assert result.outcome=='succeeded',result.diagnostics
        material,evidence=result.output('material'),result.output('evidence')
    assert material.data==b'%PDF-1.7\noriginal'
    assert evidence.material_identity==material.identity
    assert evidence.observed_at==datetime(2026,11,23,tzinfo=timezone.utc)
    assert evidence.observed_origin_assurance=='provider_reported'
    assert evidence.transport_assurance=='peer_bound'
    assert evidence.logical_target_identity==sha256(request.url.encode()).hexdigest()
    assert evidence.actual_target_identity==sha256(backend.calls[0].url.encode()).hexdigest()
    assert evidence.logical_target_identity!=evidence.actual_target_identity
    assert evidence.route_id==route.route_id


def test_provider_reported_origin_is_retained_with_its_actual_strength():
    class Reported:
        def fetch(self,request):
            return HttpResponse(200,b'data',{},datetime(2026,11,23,tzinfo=timezone.utc),'https://publisher.example')
    with StrategyBox(providers={'http':Reported()}) as box:
        result=box.invoke('command.material.fetch',inputs={'request':RequestSpec('https://publisher.example/data')})
        assert result.outcome=='succeeded',result.diagnostics
        evidence=result.output('evidence')
    assert evidence.observed_origin_assurance=='provider_reported'
    assert evidence.transport_assurance in {None,'provider_reported'}


def test_response_size_limit_rejects_material_before_handoff():
    with StrategyBox(providers={'http':lambda request:b'too long'}) as box:
        result=box.invoke('command.material.fetch',inputs={'request':RequestSpec('https://publisher.example/data',max_bytes=1)})
    assert result.outcome=='failed' and 'material' not in result.outputs
