"""Explicit subject presentation choices over already admitted coordinates."""
from collections.abc import Mapping

from stratbox.shared.data.selection import SubjectChoice


def subject_choices(rows, parameters):
    supplied = parameters.get("subject_selection", parameters.get("subjects"))
    if supplied is None:
        return None
    if isinstance(supplied, (str, bytes)):
        raise ValueError("cbr.subject_selection_invalid")
    observed = {}
    for row in rows:
        observed.setdefault(str(row["subject"]), set()).add(str(row["subject_namespace"]))
    choices = []
    for value in supplied:
        if isinstance(value, SubjectChoice):
            choice = value
        elif isinstance(value, Mapping):
            choice = SubjectChoice(**value)
        elif isinstance(value, str) and len(observed.get(value, ())) == 1:
            choice = SubjectChoice(next(iter(observed[value])), value)
        else:
            raise ValueError("cbr.subject_namespace_required")
        choices.append(choice)
    keys = [(choice.namespace, choice.subject_id) for choice in choices]
    if len(keys) != len(set(keys)):
        raise ValueError("cbr.subject_selection_duplicate")
    return tuple(choices)


def select_subject_rows(rows, choices):
    if choices is None:
        return tuple(rows), ()
    lookup = {(choice.namespace, choice.subject_id): (ordinal, choice)
              for ordinal, choice in enumerate(choices)}
    selected, observed = [], set()
    for row in rows:
        key = str(row["subject_namespace"]), str(row["subject"])
        if key not in lookup:
            continue
        ordinal, choice = lookup[key]
        item = dict(row)
        item["subject_order"] = ordinal
        if choice.label is not None:
            item["subject_label"] = choice.label
        if choice.reference_identity is not None:
            item["subject_reference"] = choice.reference_identity
        selected.append(item)
        observed.add(key)
    selected.sort(key=lambda row: lookup[(str(row["subject_namespace"]), str(row["subject"]))][0])
    missing = tuple(key for key in lookup if key not in observed)
    return tuple(selected), missing
