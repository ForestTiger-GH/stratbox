"""Explicit issue inputs qualify a series interpretation without a hidden lookup."""
from collections.abc import Mapping
from pathlib import PurePosixPath
from urllib.parse import urlsplit
from stratbox.shared.data.values import PublicationAsset, SourceClaim


def issue_parameters(inputs, context, retained_issue=""):
    result = dict(context.parameters)
    supplied = inputs.get("issue")
    if isinstance(supplied, PublicationAsset):
        details = {"issue_id": supplied.issue_id, "source_name": PurePosixPath(urlsplit(supplied.locator).path).name}
    elif isinstance(supplied, SourceClaim):
        details = {"issue_id": supplied.issue_id}
    elif isinstance(supplied, str):
        details = {"issue_id": supplied}
    elif isinstance(supplied, Mapping):
        details = dict(supplied)
    elif supplied is None:
        details = {}
    else:
        raise ValueError("cbr.issue_input_unqualified")
    for key, value in details.items():
        if key in result and result[key] != value:
            raise ValueError("cbr.issue_input_conflict")
        result[key] = value
    if "issue_id" not in result and retained_issue:
        result["issue_id"] = retained_issue
    if retained_issue and result.get("issue_id", retained_issue) != retained_issue:
        raise ValueError("cbr.issue_input_conflict")
    return result
