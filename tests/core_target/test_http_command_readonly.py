"""Read acquisition must reject mutation-capable POST before invoking a provider."""
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material, RequestSpec


class Provider:
    def __init__(self):
        self.calls=0
    def fetch(self,request):
        self.calls+=1
        return Material(b"source response")


def test_concurrent_post_without_readonly_declaration_is_rejected_before_provider_call():
    provider=Provider()
    request=RequestSpec("https://example.test/report",method="POST",body=b"x=1",
        read_only=False,observation_id="same-observation")
    with StrategyBox(providers={"http":provider}) as box:
        first=box.submit("command.material.fetch",inputs={"request":request})
        second=box.submit("command.material.fetch",inputs={"request":request})
        results=(first.result(timeout=3),second.result(timeout=3))
        assert all(result.outcome=="failed" for result in results)
        assert all(not result.outputs for result in results)
    assert provider.calls==0


def test_explicit_readonly_post_remains_an_admitted_source_acquisition():
    provider=Provider()
    request=RequestSpec("https://rmsp.nalog.ru/statistics-proc.json",method="POST",
        form={"statDate":"10.11.2026"},read_only=True)
    with StrategyBox(providers={"http":provider}) as box:
        result=box.invoke("command.material.fetch",inputs={"request":request})
        assert result.outcome=="succeeded" and result.output("material").data==b"source response"
    assert provider.calls==1
