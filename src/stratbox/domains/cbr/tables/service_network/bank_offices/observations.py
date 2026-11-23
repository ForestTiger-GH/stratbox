"""Source-local observation projection independent of acquisition and storage."""
import re
from stratbox.shared.data.observations import MetricRef, Observation, PeriodRef, SubjectRef

def _observations(rows, captured_on, official_as_of):
    period = (
        PeriodRef("as_of", official_as_of)
        if official_as_of is not None
        else PeriodRef("capture", captured_on)
    )
    observations = []
    for source_row, section, region, _bank, registration, *tokens in rows[1:]:
        for header, token in zip(rows[0][5:], tokens):
            value = (
                int(token)
                if re.fullmatch(r"[0-9]{1,18}", token, re.ASCII)
                else token or None
            )
            status = "reported"
            if token in {"", "-", "–", "—"}:
                status = "blank" if not token else "dash"
                value = None
            observations.append(
                Observation(
                    SubjectRef("cbr.bank.registration", registration),
                    MetricRef(header, "count"),
                    period,
                    (("region", region), ("section", section)),
                    "published_bank_region",
                    value,
                    status,
                    f"row:{source_row}",
                    token,
                )
            )
    return tuple(observations)
