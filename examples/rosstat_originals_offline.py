"""Offline publication recognition, exact original storage and notification.

A synthetic HTML anchor and a fake PDF envelope exercise only technical source
boundaries. They certify no publisher issue, numerical table or live website.
"""
from tempfile import TemporaryDirectory

from stratbox.capabilities.model.targets import FeedTarget
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


class OfflineHTTP:
    def fetch(self, request):
        return Material(b"%PDF-1.4\n% explicit synthetic envelope\n%%EOF\n", "application/pdf",
            request.source_id, metadata=request.metadata)


class Inbox:
    scope_id="example.rosstat.offline-inbox"
    def __init__(self):
        self.receipts = {}

    def deliver(self, intent):
        self.receipts.setdefault(intent["id"], {"status": "confirmed", "channel": "offline-inbox"})
        return self.receipts[intent["id"]]

    def lookup(self, effect_id):
        return self.receipts.get(effect_id)


def required(result, output):
    if result.outcome != "succeeded":
        raise RuntimeError(result.diagnostics)
    return result.output(output)


def main():
    source_id = "rosstat.socioeconomic_russia"
    target = FeedTarget(source_id)
    page = Material(b'<a href="/storage/mediabank/osn-08-2026.pdf">2026-08</a>',
        "text/html", source_id + ".index")
    inbox = Inbox()
    with TemporaryDirectory() as location, StrategyBox(providers={
        "http": OfflineHTTP(), "filestore": LocalFileStore(location), "notification": inbox,
    }) as box:
        listing = required(box.invoke("command.publication.scan",
            inputs={"index": page}, target=target), "listing")
        selection = required(box.invoke("command.issue.select",
            inputs={"listing": listing, "query": {"issue_id": "2026-08", "asset_id": "report"}},
            target=target), "selection")
        asset, = selection.entries
        acquired = box.invoke("operation.material.acquire", inputs={"locator": asset}, target=target)
        identified = required(acquired, "material")
        assessment = required(box.invoke("command.source.assess",
            inputs={"evidence": identified.material}, target=target), "assessment")
        assert assessment.status == "first_seen"
        committed = box.invoke("command.artifact.commit",
            inputs={"material": identified.material, "destination": "originals"})
        reference = required(committed, "reference")
        notification_page = box.session.journal.read_page(run_id=committed.run_id)
        intents = required(box.invoke("command.notification.prepare", inputs={"page": notification_page},
            parameters={"subscription_id": "offline-originals", "route": "offline-inbox",
                "selector": {"run_id": committed.run_id, "kind": "output.accepted",
                    "output_name": "reference", "command_id": "command.artifact.commit"}}), "intents")
        for intent in intents:
            required(box.invoke("command.notification.deliver", inputs={"intent": intent}), "receipt")
        print({"assessment": assessment.status, "inventory": listing.assessment.status,
            "stored": reference.identity.sha256, "offline_notifications": len(inbox.receipts)})


if __name__ == "__main__":
    main()
