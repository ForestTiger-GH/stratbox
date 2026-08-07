from __future__ import annotations

from dataclasses import dataclass, replace
from math import isfinite

import numpy as np
import pandas as pd

from stratbox.macrobanks.cbr_sors_restoration.contracts import SorsSourceBundle
from stratbox.macrobanks.cbr_sors_restoration.linear.contracts import (
    CsrMatrixData,
    LinearTarget,
    SorsLinearProblem,
)
from stratbox.macrobanks.cbr_sors_restoration.metrics import METRIC_COMPONENTS
from stratbox.macrobanks.cbr_sors_restoration.portfolio import PRIMARY_PORTFOLIO_SCOPE
from stratbox.macrobanks.cbr_sors_restoration.publication import (
    solver_lower_bound,
    solver_upper_bound,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.quantities import (
    SorsQuantityGraph,
    component_quantity_id,
    metric_quantity_id,
)
from stratbox.macrobanks.cbr_sors_restoration.strict.reduction import assign_connected_components


@dataclass(frozen=True)
class StrictCompilation:
    problem: SorsLinearProblem
    target_catalog_grid: pd.DataFrame


def _csr(rows: list[list[tuple[int, float]]], n_columns: int) -> CsrMatrixData:
    indptr = [0]
    indices: list[int] = []
    data: list[float] = []
    for row in rows:
        for column, coefficient in sorted(row):
            if coefficient == 0:
                continue
            indices.append(int(column))
            data.append(float(coefficient))
        indptr.append(len(indices))
    return CsrMatrixData(
        shape=(len(rows), n_columns),
        indptr=np.asarray(indptr, dtype=np.int64),
        indices=np.asarray(indices, dtype=np.int32),
        data=np.asarray(data, dtype=float),
    )


def compile_strict_problem(
    bundle: SorsSourceBundle,
    graph: SorsQuantityGraph,
    quantities_grid: pd.DataFrame,
    *,
    point_tolerance: float,
) -> StrictCompilation:
    """Compile one latent LP for corporate, SME and SME-IE together.

    All three scopes have their own atomic variables.  Exact portfolio nesting is
    encoded as ``SME_IE <= SME <= CORPORATE_TOTAL`` on every atomic component.
    User-facing optimization targets are deliberately emitted only for the primary
    corporate scope; the segment cubes remain pure auxiliary constraints.
    """

    quantities = quantities_grid.set_index('quantity_id', drop=False)
    components = quantities[
        quantities['quantity_kind'].eq('ATOMIC_COMPONENT')
    ].sort_values(['portfolio_scope','region_code','class_code','component']).copy()
    fixed = (
        np.isfinite(components['upper_bound'].astype(float))
        & (components['upper_bound'].astype(float)-components['lower_bound'].astype(float)).abs().le(point_tolerance)
        & components['lower_attained'].astype(bool)
        & components['upper_attained'].astype(bool)
    )
    components['is_fixed'] = fixed
    components['fixed_value'] = np.where(
        fixed,
        (components['lower_bound'].astype(float)+components['upper_bound'].astype(float))/2.0,
        np.nan,
    )
    active_ids = tuple(components.loc[~fixed,'quantity_id'].astype(str))
    column_by_quantity = {quantity_id: i for i, quantity_id in enumerate(active_ids)}
    components['solver_column'] = components['quantity_id'].map(column_by_quantity)
    components['original_variable_id'] = components['quantity_id']
    fixed_values = components.set_index('quantity_id')['fixed_value'].to_dict()

    active_rows = components.loc[~fixed]
    active_lower = np.asarray([
        solver_lower_bound(row.lower_bound, bool(row.lower_attained), open_margin=point_tolerance)
        for row in active_rows.itertuples(index=False)
    ], dtype=float)
    active_upper = np.asarray([
        solver_upper_bound(row.upper_bound, bool(row.upper_attained), open_margin=point_tolerance)
        for row in active_rows.itertuples(index=False)
    ], dtype=float)

    rows: list[list[tuple[int,float]]] = []
    row_lower: list[float] = []
    row_upper: list[float] = []
    row_meta: list[dict[str,object]] = []
    row_columns: list[np.ndarray] = []

    def component_expression(scope: str, region_code: str, class_code: str, metric: str):
        coefficient_by_column: dict[int,float] = {}
        fixed_offset = 0.0
        for component in METRIC_COMPONENTS[metric]:
            component_id = component_quantity_id(scope, region_code, class_code, component)
            column = column_by_quantity.get(component_id)
            if column is None:
                fixed_offset += float(fixed_values[component_id])
            else:
                coefficient_by_column[column] = coefficient_by_column.get(column,0.0)+1.0
        items = [(column,coef) for column,coef in coefficient_by_column.items() if coef]
        columns = np.asarray([x[0] for x in items], dtype=np.int32)
        coefficients = np.asarray([x[1] for x in items], dtype=float)
        return items, columns, coefficients, fixed_offset

    exact_relations = graph.relations_grid[
        ~graph.relations_grid['relation_kind'].astype(str).eq('DOMINANCE')
    ].set_index('parent_quantity_id')
    publication = quantities[quantities['quantity_kind'].eq('PUBLISHED_AGGREGATE')].sort_index()
    binding_map = (
        graph.observation_bindings_grid.groupby('quantity_id', sort=False)[['observation_id','source_series']]
        .agg(tuple).to_dict('index')
        if not graph.observation_bindings_grid.empty else {}
    )

    for pub in publication.itertuples(index=False):
        relation = exact_relations.loc[str(pub.quantity_id)]
        if isinstance(relation, pd.DataFrame):
            relation = relation.iloc[0]
        coefficient_by_column: dict[int,float] = {}
        fixed_offset = 0.0
        for metric_quantity_id_value in relation.child_quantity_ids:
            metric_row = quantities.loc[str(metric_quantity_id_value)]
            if isinstance(metric_row, pd.DataFrame):
                raise ValueError(f'Duplicate metric quantity {metric_quantity_id_value}')
            scope = str(metric_row.portfolio_scope)
            region_code = str(metric_row.region_code)
            class_code = str(metric_row.class_code)
            metric = str(metric_row.metric)
            for component in METRIC_COMPONENTS[metric]:
                component_id = component_quantity_id(scope,region_code,class_code,component)
                column = column_by_quantity.get(component_id)
                if column is None:
                    fixed_offset += float(fixed_values[component_id])
                else:
                    coefficient_by_column[column] = coefficient_by_column.get(column,0.0)+1.0
        items = [(column,coef) for column,coef in coefficient_by_column.items() if coef]
        columns = np.asarray([x[0] for x in items],dtype=np.int32)
        coefficients = np.asarray([x[1] for x in items],dtype=float)
        semantic_lower = float(pub.lower_bound)-fixed_offset
        semantic_upper = float(pub.upper_bound)-fixed_offset
        lower = solver_lower_bound(semantic_lower,bool(pub.lower_attained),open_margin=point_tolerance)
        upper = solver_upper_bound(semantic_upper,bool(pub.upper_attained),open_margin=point_tolerance)
        if len(columns):
            expression_lower = float(np.dot(coefficients,np.where(coefficients>=0,active_lower[columns],active_upper[columns])))
            expression_upper = float(np.dot(coefficients,np.where(coefficients>=0,active_upper[columns],active_lower[columns])))
        else:
            expression_lower=expression_upper=0.0
        redundant=(expression_lower>=lower-point_tolerance and expression_upper<=upper+point_tolerance)
        solver_row=None
        if items:
            solver_row=len(rows); rows.append(items); row_lower.append(lower); row_upper.append(upper); row_columns.append(columns)
            status='REDUNDANT_AT_COMPILE' if redundant else 'ACTIVE'
        else:
            if not redundant:
                raise ValueError(f'Publication constraint {pub.quantity_id} has no active variables and is not satisfied')
            status='FIXED_EXPRESSION'
        binding=binding_map.get(str(pub.quantity_id),{})
        representative=getattr(pub,'published_representative',None)
        representative_status=getattr(pub,'published_representative_status',None)
        stable_center=(float(representative)-fixed_offset if representative_status=='STABLE' and representative is not None and not pd.isna(representative) else None)
        row_meta.append({
            'constraint_id':f'strict:{pub.quantity_id}',
            'quantity_id':str(pub.quantity_id),
            'portfolio_scope':str(pub.portfolio_scope),
            'constraint_kind':str(relation.relation_kind),
            'model_layer':'STRICT',
            'source_observation_ids':binding.get('observation_id',()),
            'source_series':binding.get('source_series',()),
            'lower_bound':semantic_lower,'upper_bound':semantic_upper,
            'lower_attained':bool(pub.lower_attained),'upper_attained':bool(pub.upper_attained),
            'solver_lower_bound':lower,'solver_upper_bound':upper,'fixed_offset':fixed_offset,
            'published_representative':representative,
            'published_representative_status':representative_status,
            'published_center':stable_center,'constraint_status':status,'solver_row':solver_row,
            'active_columns':len(items),'expression_indices':columns,'expression_coefficients':coefficients,
        })

    # Stable dynamic metric rows for all scopes preserve correlations introduced by
    # publication facts discovered after compilation.
    regional_metrics = quantities[quantities['quantity_kind'].eq('REGIONAL_CLASS_METRIC')].copy()
    if not regional_metrics.empty:
        regional_metrics = regional_metrics.sort_values(
            ['portfolio_scope', 'region_code', 'class_code', 'metric']
        )
    for metric_row in regional_metrics.itertuples(index=False):
        scope=str(metric_row.portfolio_scope); region_code=str(metric_row.region_code); class_code=str(metric_row.class_code); metric=str(metric_row.metric)
        items,columns,coefficients,fixed_offset=component_expression(scope,region_code,class_code,metric)
        semantic_lower=float(metric_row.lower_bound)-fixed_offset
        semantic_upper=float(metric_row.upper_bound)-fixed_offset
        solver_row=None
        if items:
            solver_row=len(rows); rows.append(items)
            row_lower.append(solver_lower_bound(semantic_lower,bool(metric_row.lower_attained),open_margin=point_tolerance))
            row_upper.append(solver_upper_bound(semantic_upper,bool(metric_row.upper_attained),open_margin=point_tolerance))
            row_columns.append(columns)
        row_meta.append({
            'constraint_id':f'dynamic_metric:{metric_row.quantity_id}',
            'quantity_id':str(metric_row.quantity_id),'portfolio_scope':scope,
            'constraint_kind':'REGIONAL_CLASS_METRIC_BOUND','model_layer':'PUBLICATION_DYNAMIC',
            'source_observation_ids':(),'source_series':(),
            'lower_bound':semantic_lower,'upper_bound':semantic_upper,
            'lower_attained':bool(metric_row.lower_attained),'upper_attained':bool(metric_row.upper_attained),
            'solver_lower_bound':row_lower[solver_row] if solver_row is not None else semantic_lower,
            'solver_upper_bound':row_upper[solver_row] if solver_row is not None else semantic_upper,
            'fixed_offset':fixed_offset,'published_representative':None,
            'published_representative_status':None,'published_center':None,
            'constraint_status':'DYNAMIC_ACTIVE' if solver_row is not None else 'FIXED_EXPRESSION',
            'solver_row':solver_row,'active_columns':len(items),'expression_indices':columns,
            'expression_coefficients':coefficients,
        })

    # Exact nested-scope inequalities on atomic components.  Other dominance rows
    # are mathematically implied by these and by metric-component sums, so they stay
    # in deterministic closure only and do not bloat the LP further.
    dominance = graph.relations_grid[
        graph.relations_grid['relation_kind'].astype(str).eq('DOMINANCE')
        & graph.relations_grid.get('dominance_kind', pd.Series(index=graph.relations_grid.index,dtype=object)).astype(str).eq('PORTFOLIO_SCOPE_COMPONENT')
    ]
    for rel in dominance.itertuples(index=False):
        parent_id=str(rel.parent_quantity_id); child_id=str(tuple(rel.child_quantity_ids)[0])
        coefficient_by_column: dict[int,float] = {}
        constant=0.0
        for quantity_id,coef in ((child_id,1.0),(parent_id,-1.0)):
            column=column_by_quantity.get(quantity_id)
            if column is None:
                constant += coef*float(fixed_values[quantity_id])
            else:
                coefficient_by_column[column]=coefficient_by_column.get(column,0.0)+coef
        items=[(c,v) for c,v in coefficient_by_column.items() if v]
        columns=np.asarray([x[0] for x in items],dtype=np.int32)
        coefficients=np.asarray([x[1] for x in items],dtype=float)
        upper=-constant
        solver_row=None
        if items:
            solver_row=len(rows); rows.append(items); row_lower.append(-np.inf); row_upper.append(upper); row_columns.append(columns)
        elif constant>point_tolerance:
            raise ValueError(f'Fixed portfolio nesting relation is violated: {rel.relation_id}')
        row_meta.append({
            'constraint_id':f'strict:{rel.relation_id}','quantity_id':None,'portfolio_scope':None,
            'constraint_kind':'PORTFOLIO_SCOPE_COMPONENT_DOMINANCE','model_layer':'STRICT_DOMINANCE',
            'source_observation_ids':(),'source_series':(),'lower_bound':-np.inf,'upper_bound':upper,
            'lower_attained':False,'upper_attained':True,'solver_lower_bound':-np.inf,'solver_upper_bound':upper,
            'fixed_offset':constant,'published_representative':None,'published_representative_status':None,
            'published_center':None,'constraint_status':'ACTIVE' if solver_row is not None else 'FIXED_EXPRESSION',
            'solver_row':solver_row,'active_columns':len(items),'expression_indices':columns,
            'expression_coefficients':coefficients,'relation_id':str(rel.relation_id),
        })

    variables_grid=components.reset_index(drop=True)
    variables_grid=assign_connected_components(variables_grid,row_columns)
    active=variables_grid[~variables_grid['is_fixed'].astype(bool)].sort_values('solver_column')
    problem=SorsLinearProblem(
        model_layer='STRICT',matrix=_csr(rows,len(active)),
        row_lower=np.asarray(row_lower,dtype=float),row_upper=np.asarray(row_upper,dtype=float),
        col_lower=active_lower,col_upper=active_upper,objective=np.zeros(len(active),dtype=float),
        constraints_grid=pd.DataFrame(row_meta),variables_grid=variables_grid,
        metadata={'quantity_to_column':column_by_quantity,'fixed_values':fixed_values,'point_tolerance':point_tolerance,'primary_portfolio_scope':PRIMARY_PORTFOLIO_SCOPE},
    )

    region_meta=bundle.atomic_regions_grid.set_index('region_code').to_dict('index')
    class_meta=bundle.okved2_classes_grid.set_index('class_code').to_dict('index')
    connected_by_quantity=variables_grid.set_index('quantity_id')['connected_component_id'].to_dict()
    target_rows:list[dict[str,object]]=[]
    for region in bundle.atomic_regions_grid.sort_values('region_order').itertuples(index=False):
        region_code=str(region.region_code)
        for activity in bundle.okved2_classes_grid.sort_values('class_order').itertuples(index=False):
            class_code=str(activity.class_code)
            for metric in METRIC_COMPONENTS:
                quantity_id=metric_quantity_id(PRIMARY_PORTFOLIO_SCOPE,region_code,class_code,metric)
                columns=[]; coefficients=[]; constant=0.0; connected:set[str]=set()
                for component in METRIC_COMPONENTS[metric]:
                    component_id=component_quantity_id(PRIMARY_PORTFOLIO_SCOPE,region_code,class_code,component)
                    column=column_by_quantity.get(component_id)
                    if column is None:
                        constant += float(fixed_values[component_id])
                    else:
                        columns.append(column); coefficients.append(1.0)
                        cc=connected_by_quantity.get(component_id)
                        if cc is not None and pd.notna(cc): connected.add(str(cc))
                target_rows.append({
                    'target_id':quantity_id,'target_kind':'METRIC','quantity_id':quantity_id,
                    'portfolio_scope':PRIMARY_PORTFOLIO_SCOPE,
                    'region_code':region_code,'region_name':str(region_meta[region_code]['region_name']),
                    'class_code':class_code,'class_name':str(class_meta[class_code]['class_name']),
                    'metric':metric,'component':None,'indices':np.asarray(columns,dtype=np.int32),
                    'coefficients':np.asarray(coefficients,dtype=float),'constant':constant,
                    'connected_component_ids':tuple(sorted(connected)),
                })
            for component in ('performing_rub','overdue_rub','performing_fx','overdue_fx'):
                quantity_id=component_quantity_id(PRIMARY_PORTFOLIO_SCOPE,region_code,class_code,component)
                column=column_by_quantity.get(quantity_id)
                constant=float(fixed_values[quantity_id]) if column is None else 0.0
                cc=connected_by_quantity.get(quantity_id); connected=()
                if cc is not None and pd.notna(cc): connected=(str(cc),)
                target_rows.append({
                    'target_id':quantity_id,'target_kind':'COMPONENT','quantity_id':quantity_id,
                    'portfolio_scope':PRIMARY_PORTFOLIO_SCOPE,
                    'region_code':region_code,'region_name':str(region_meta[region_code]['region_name']),
                    'class_code':class_code,'class_name':str(class_meta[class_code]['class_name']),
                    'metric':component,'component':component,
                    'indices':np.asarray([],dtype=np.int32) if column is None else np.asarray([column],dtype=np.int32),
                    'coefficients':np.asarray([],dtype=float) if column is None else np.asarray([1.0],dtype=float),
                    'constant':constant,'connected_component_ids':connected,
                })
    return StrictCompilation(problem=problem,target_catalog_grid=pd.DataFrame(target_rows))


def linear_target_from_row(row) -> LinearTarget:
    return LinearTarget(
        target_id=str(row.target_id),quantity_id=str(row.quantity_id),
        region_code=str(row.region_code),region_name=str(row.region_name),
        class_code=str(row.class_code),metric=str(row.metric),
        indices=np.asarray(row.indices,dtype=np.int32),
        coefficients=np.asarray(row.coefficients,dtype=float),constant=float(row.constant),
    )


def refresh_strict_problem_bounds(
    problem: SorsLinearProblem,
    quantities_grid: pd.DataFrame,
) -> SorsLinearProblem:
    """Refresh every mutable bound of the persistent latent Solver model.

    The deterministic publication fixed point can tighten three kinds of latent
    objects between Solver waves:

    * atomic components -> Solver column bounds;
    * official published aggregates -> stable STRICT source rows;
    * regional class metrics -> stable PUBLICATION_DYNAMIC rows.

    All three are refreshed from one authoritative ``quantities_grid``.  Matrix
    structure and column identities never change, so target expressions and the
    persistent HiGHS model remain reusable.
    """

    open_margin = float(problem.metadata.get('point_tolerance', 0.0))
    quantities = quantities_grid.set_index('quantity_id', drop=False)

    active = problem.variables_grid[
        problem.variables_grid['solver_column'].notna()
    ][['quantity_id', 'solver_column']].copy()
    active['solver_column'] = active['solver_column'].astype(int)
    active = active.sort_values('solver_column')
    quantity_ids = active['quantity_id'].astype(str).to_numpy()
    aligned = quantities.reindex(quantity_ids)
    if aligned['quantity_id'].isna().any():
        missing = tuple(quantity_ids[aligned['quantity_id'].isna().to_numpy()])
        raise ValueError(
            f'Unknown Solver quantity IDs while refreshing bounds: {missing[:10]}'
        )

    lower = aligned['lower_bound'].astype(float).to_numpy(copy=True)
    upper = aligned['upper_bound'].astype(float).to_numpy(copy=True)
    lower_attained = aligned['lower_attained'].astype(bool).to_numpy()
    upper_attained = aligned['upper_attained'].astype(bool).to_numpy()

    lower_open = (~lower_attained) & np.isfinite(lower)
    upper_open = (~upper_attained) & np.isfinite(upper)
    if lower_open.any():
        adjacent = np.nextafter(lower[lower_open], np.inf)
        lower[lower_open] = np.maximum(adjacent, lower[lower_open] + open_margin)
    if upper_open.any():
        adjacent = np.nextafter(upper[upper_open], -np.inf)
        upper[upper_open] = np.minimum(adjacent, upper[upper_open] - open_margin)

    row_lower = problem.row_lower.astype(float).copy()
    row_upper = problem.row_upper.astype(float).copy()
    constraints = problem.constraints_grid.copy()

    refreshable = constraints[
        constraints['quantity_id'].notna()
        & constraints['constraint_kind'].astype(str).isin(
            [
                'REGIONAL_CLASS_METRIC_BOUND',
                # Official rows keep their original relation kind, so model_layer
                # rather than a fixed list identifies them below.
            ]
        )
    ].copy()
    official = constraints[
        constraints['model_layer'].astype(str).eq('STRICT')
        & constraints['quantity_id'].notna()
    ].copy()
    if not official.empty:
        refreshable = pd.concat([refreshable, official], ignore_index=False).drop_duplicates(
            'constraint_id', keep='first'
        )

    if not refreshable.empty:
        # Refreshing rows one-by-one with a full-frame boolean mask is O(N²) on
        # the production model (~46k mutable rows).  Constraint indices are
        # stable structural identities, so align quantities once and update the
        # complete row block vectorially.
        refresh_indices = refreshable.index.to_numpy()
        refresh_quantity_ids = refreshable['quantity_id'].astype(str).to_numpy()
        refreshed_quantities = quantities.reindex(refresh_quantity_ids)
        if refreshed_quantities['quantity_id'].isna().any():
            missing = tuple(
                refresh_quantity_ids[
                    refreshed_quantities['quantity_id'].isna().to_numpy()
                ]
            )
            raise ValueError(
                'Unknown constraint quantities while refreshing Solver rows: '
                f'{missing[:10]}'
            )

        fixed_offsets = (
            pd.to_numeric(refreshable.get('fixed_offset', 0.0), errors='coerce')
            .fillna(0.0)
            .to_numpy(dtype=float)
            if 'fixed_offset' in refreshable
            else np.zeros(len(refreshable), dtype=float)
        )
        semantic_lower = (
            refreshed_quantities['lower_bound'].to_numpy(dtype=float) - fixed_offsets
        )
        semantic_upper = (
            refreshed_quantities['upper_bound'].to_numpy(dtype=float) - fixed_offsets
        )
        attained_lower = refreshed_quantities['lower_attained'].to_numpy(dtype=bool)
        attained_upper = refreshed_quantities['upper_attained'].to_numpy(dtype=bool)

        solver_lower = semantic_lower.copy()
        solver_upper = semantic_upper.copy()
        finite_lower = np.isfinite(solver_lower)
        finite_upper = np.isfinite(solver_upper)
        open_lower = finite_lower & ~attained_lower
        open_upper = finite_upper & ~attained_upper
        if open_lower.any():
            adjacent = np.nextafter(solver_lower[open_lower], np.inf)
            solver_lower[open_lower] = np.maximum(
                adjacent, solver_lower[open_lower] + open_margin
            )
        if open_upper.any():
            adjacent = np.nextafter(solver_upper[open_upper], -np.inf)
            solver_upper[open_upper] = np.minimum(
                adjacent, solver_upper[open_upper] - open_margin
            )

        constraints.loc[refresh_indices, 'lower_bound'] = semantic_lower
        constraints.loc[refresh_indices, 'upper_bound'] = semantic_upper
        constraints.loc[refresh_indices, 'lower_attained'] = attained_lower
        constraints.loc[refresh_indices, 'upper_attained'] = attained_upper
        constraints.loc[refresh_indices, 'solver_lower_bound'] = solver_lower
        constraints.loc[refresh_indices, 'solver_upper_bound'] = solver_upper

        solver_rows = pd.to_numeric(refreshable['solver_row'], errors='coerce')
        active_rows = solver_rows.notna().to_numpy()
        if active_rows.any():
            row_indices = solver_rows.to_numpy(dtype=float)[active_rows].astype(int)
            row_lower[row_indices] = solver_lower[active_rows]
            row_upper[row_indices] = solver_upper[active_rows]

    return replace(
        problem,
        col_lower=lower,
        col_upper=upper,
        row_lower=row_lower,
        row_upper=row_upper,
        constraints_grid=constraints,
    )

