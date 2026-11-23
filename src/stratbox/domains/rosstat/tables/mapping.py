"""Explicit reviewed profiles for Russia reports, regional members and population.

A byte-bound reviewed profile supplies semantics. A PDF page text is not silently
promoted to a table: only structured document table blocks may bind coordinates.
"""
from stratbox.shared.data.snapshots import SnapshotCoverage
from stratbox.shared.evidence import UsedInputReceipt
from .contracts import ReviewedTableProfile, RosstatSourceFlake, SourceValue
from .kep2 import numeric_token, _raw


def map_reviewed_cells(physical, profile: ReviewedTableProfile) -> RosstatSourceFlake:
    if physical.series_id != profile.series_id or physical.source_identity != profile.source_identity:
        raise ValueError("rosstat.profile_source_mismatch")
    allowed={"rosstat.socioeconomic_russia","rosstat.socioeconomic_regions",
             "rosstat.short_term_indicators","rosstat.population_municipalities"}
    if profile.series_id not in allowed:
        raise ValueError("rosstat.series_unknown")
    workbooks=hasattr(physical,"sheets")
    if workbooks:
        cells={sheet.name:{(cell.row,cell.column):cell for cell in sheet.cells} for sheet in physical.sheets}
        sheets={sheet.name:sheet for sheet in physical.sheets}
    else:
        blocks={str(block.ordinal):block for block in physical.blocks}
        for block in physical.blocks:
            if block.locator:
                if block.locator in blocks and blocks[block.locator] != block:
                    raise ValueError("rosstat.document_locator_ambiguous")
                blocks[block.locator]=block
    values,diagnostics=[],[]
    lineage=list(physical.lineage)
    if profile.territory_edition is not None:
        lineage.extend(receipt for receipt in profile.territory_edition.lineage if receipt not in lineage)
        lineage.append(UsedInputReceipt("territory_edition",profile.territory_edition.identity,"application/vnd.stratbox.dataset","inline"))
    for binding in profile.bindings:
        formula=False
        if workbooks:
            if binding.sheet not in cells or binding.block_id:
                raise ValueError("rosstat.profile_sheet_missing")
            sheet=sheets[binding.sheet]
            if binding.row > sheet.rows or binding.column > sheet.columns:
                raise ValueError("rosstat.profile_coordinate_outside_source")
            cell=cells[binding.sheet].get((binding.row,binding.column))
            raw=_raw(cell)
            formula=bool(cell and cell.formula and cell.value is None)
        else:
            if binding.block_id not in blocks or binding.sheet:
                raise ValueError("rosstat.profile_block_missing")
            block=blocks[binding.block_id]
            if block.kind != "table" or not block.rows:
                raise ValueError("rosstat.profile_structured_table_required")
            if binding.row > len(block.rows) or binding.column > len(block.rows[binding.row-1]):
                raise ValueError("rosstat.profile_coordinate_outside_source")
            raw=block.rows[binding.row-1][binding.column-1]
        value,status,notes=numeric_token(raw,formula_without_cache=formula)
        if status == "unparsed":
            diagnostics.append("rosstat.profile.unparsed:" + binding.source_locator)
        if profile.series_id == "rosstat.population_municipalities":
            if binding.quantity_kind != "count" or binding.period_kind != "as_of":
                raise ValueError("rosstat.population_stock_date_required")
            if binding.geography_namespace not in {"oktmo","okato","iso3166-1"}:
                raise ValueError("rosstat.population_geography_profile_required")
            if binding.geography_namespace in {"oktmo","okato"} and not any(k == "geography_edition" for k,_ in binding.dimensions):
                raise ValueError("rosstat.population_geography_edition_required")
            if binding.geography_namespace in {"oktmo","okato"}:
                edition=profile.territory_edition
                if edition is None or dict(binding.dimensions).get("geography_edition") != edition.edition_id:
                    raise ValueError("rosstat.population_territory_reference_required")
                territory=edition.resolve(binding.geography_namespace,binding.geography_id,as_of=binding.period_start)
                if territory is None:
                    raise ValueError("rosstat.population_territory_date_unresolved")
                if binding.perimeter != territory.perimeter_id:
                    raise ValueError("rosstat.population_perimeter_mismatch")
        values.append(SourceValue(binding.indicator_id,binding.label,binding.measure,binding.frequency,
            binding.period_start,binding.period_end,binding.display_date or binding.period_end,
            value,status,raw,binding.unit_literal,binding.unit,binding.scale,binding.quantity_kind,
            binding.geography_namespace,binding.geography_id,binding.source_locator,binding.sheet,
            binding.row,binding.column,binding.footnotes + notes,binding.dimensions,binding.perimeter,binding.period_kind,
            cell.kind if workbooks and cell else "document_text" if not workbooks else "absent",
            cell.number_format if workbooks and cell else "General",cell.formula if workbooks and cell else None))
    return RosstatSourceFlake(physical.series_id,physical.issue_id,physical.asset_id,physical.source_identity,
        physical.identity,profile.profile_id,profile.version,tuple(values),(),(),tuple(lineage),
        SnapshotCoverage("partial" if diagnostics else "complete",profile.coverage_description + "; review: " + profile.review_evidence),
        tuple(diagnostics))
