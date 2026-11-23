"""Dated municipal codes, administrative hierarchy and durable supplied evidence."""
from dataclasses import replace
from datetime import date

import pytest

from stratbox.shared.reference.geography.editions import TerritoryUnit, TerritoryEdition, territory_snapshot, territory_from_snapshot
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import SourcePayload, UsedInputReceipt


def edition():
    source=SourcePayload(b"explicit reviewed edition")
    units=(TerritoryUnit("oktmo","01","Subject","subject",date(2020,1,1),None,None,None,"subject-p","row:1"),
        TerritoryUnit("oktmo","01001","Town","urban_okrug",date(2020,1,1),date(2025,12,31),"oktmo","01","old-p","row:2"),
        TerritoryUnit("oktmo","01001","Town","municipal_okrug",date(2026,1,1),None,"oktmo","01","new-p","row:3"))
    return TerritoryEdition("example.territories","2026",units,(),
        (UsedInputReceipt.for_payload(source,"reference"),),SnapshotCoverage("partial","An explicit reviewed subset."))


def test_codes_dates_and_changed_perimeters_survive_cold_replay():
    value=territory_from_snapshot(territory_snapshot(edition()))
    assert value.resolve("oktmo","01001",as_of=date(2025,12,31)).perimeter_id=="old-p"
    assert value.resolve("oktmo","01001",as_of=date(2026,1,1)).perimeter_id=="new-p"
    assert value.resolve("okato","01001",as_of=date(2026,1,1)) is None
    assert [u.code for u in value.ancestors("oktmo","01001",as_of=date(2026,1,1))]==["01001","01"]


def test_overlapping_codes_and_cycles_are_not_silently_resolved():
    value=edition()
    with pytest.raises(ValueError,match="overlapping_code_validity"):
        replace(value,units=(*value.units,replace(value.units[-1],effective_from=date(2025,1,1))))
    cyclic=replace(value,units=(replace(value.units[0],parent_namespace="oktmo",parent_code="01001"),*value.units[1:]))
    with pytest.raises(ValueError,match="hierarchy_cycle"):
        cyclic.ancestors("oktmo","01001",as_of=date(2026,1,1))
