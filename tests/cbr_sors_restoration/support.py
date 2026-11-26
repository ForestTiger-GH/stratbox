"""Explicit source interpretation and standard numerical route for regressions."""
from dataclasses import fields, replace
from types import SimpleNamespace
from pathlib import Path

from stratbox.domains.cbr.calculations.sors import stages
from stratbox.domains.cbr.calculations.sors.inputs.contracts import SorsSourceInputs
from stratbox.domains.cbr.calculations.sors.inputs.dependencies import DEPENDENCIES
from stratbox.domains.cbr.calculations.sors.identity import seal_content


def interpreted_sources(files):
    from stratbox.core.formats.spreadsheets.cells import read_workbook_cells
    from stratbox.domains.cbr.domain import DOMAIN
    from stratbox.domains.cbr.methods.actions.statistics import SourceWorkbook
    from stratbox.domains.cbr.methods.tables.corporate_lending.observations import extract_observations
    from stratbox.domains.cbr.methods.tables.corporate_lending.debt.parser import parse_cbr_0105a_debt_corp_excel_bytes
    from stratbox.domains.cbr.common.contracts import SourceContentEvidence
    from stratbox.shared.data.tables import table_identity
    from stratbox.shared.evidence import SourcePayload, UsedInputReceipt
    values = {}
    for dependency in DEPENDENCIES:
        location = getattr(files, dependency.input_name, None)
        if location is None:
            values[dependency.input_name] = None
            continue
        data = Path(location).read_bytes()
        original = SourcePayload(data, source_id=str(location))
        receipt = UsedInputReceipt.for_payload(original, 'source_workbook')
        if dependency.input_name == 'regional_traditional':
            value = parse_cbr_0105a_debt_corp_excel_bytes(data, source_name=Path(location).name,
                source_id=str(location))
            value = replace(value, evidence=SourceContentEvidence(table_identity((('stream', value.df_stream),)), (receipt,)))
        else:
            decoded = read_workbook_cells(data)
            source = SourceWorkbook(dependency.series_id, '', original.identity, decoded.sheets, lineage=(receipt,))
            meaning = DOMAIN.series[dependency.series_id].commands['command.table.interpret'].settings.corporate
            value = extract_observations(source, meaning)
        values[dependency.input_name] = value
    return SorsSourceInputs(**values)


def execute_model_methods(source, config, *, crosswalk=False):
    """Mirror authored standard route explicitly; no application facade involved."""
    if crosswalk:
        from stratbox.domains.cbr.calculations.sors.crosswalk import stages as actions
    else:
        actions = stages
    context = SimpleNamespace(parameters={'config': config}, checkpoint=lambda: None)
    # Synthetic kernel fixtures enter at the already constructed model input.
    # Public source admission is separately tested against the complete publisher scope.
    bundle = source if isinstance(source, stages.SorsModelInputs) else actions.model_inputs({'datasets': source}, None, context)['bundle']
    built = actions.constraints_build({'bundle': bundle}, None, context)
    state, graph = built['state'], built['graph']
    for wave in range(100):
        for step in range(100):
            before = state.fingerprint
            state = actions.bounds_propagate({'graph': graph, 'state': state}, None, context)['state']
            candidate = actions.facts_inherit({'graph': graph, 'state': state}, None, context)['candidates']
            state = actions.facts_reconcile({'state': state, 'candidates': candidate}, None, context)['state']
            if state.converged:
                break
        else:
            raise AssertionError('deterministic route did not converge')
        problem = actions.model_compile({'graph': graph, 'state': state}, None, context)['problem']
        feasibility = actions.model_feasibility({'problem': problem}, None, context)['feasibility']
        proposal = actions.bounds_optimize({'problem': problem, 'feasibility': feasibility}, None, context)['optimization']
        state = actions.facts_reconcile({'state': state, 'optimization': proposal}, None, context)['state']
        if state.optimization_complete:
            break
    else:
        raise AssertionError('optimization route did not converge')
    problem = actions.model_compile({'graph': graph, 'state': state}, None, context)['problem']
    feasibility = actions.model_feasibility({'problem': problem}, None, context)['feasibility']
    return actions.values_certify({'state': state, 'feasibility': feasibility}, None, context)['values'].result
