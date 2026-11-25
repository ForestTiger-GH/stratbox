"""Prepare form product tables and independently render their workbook."""
from types import MappingProxyType
from stratbox.core.runtime.dependencies import require_extra
from stratbox.shared.data.representation import Representation, XLSX
from stratbox.core.execution import ExecutionContext, OperationFailure, OperationResult
from stratbox.core.operations.tables import record_tables, use_tables
from stratbox.domains.cbr.analytics.reporting_forms.contracts import FormData
from stratbox.domains.cbr.products.reporting_forms.contracts import FormViews
from stratbox.domains.cbr.products.reporting_forms.profiles import FORM_VIEW_PROFILES
from stratbox.domains.cbr.operations.reporting_forms.definitions import VIEWS, RENDER
from stratbox.domains.cbr.tables.reporting_forms.context import data_metadata, views_metadata

def build_form_views(request: FormData, *, invocation=None) -> OperationResult[FormViews]:

    def work(req, invocation):
        require_extra('pandas', 'dataframe')
        from stratbox.domains.cbr.products.reporting_forms.output import build_form_sheets
        invocation.stage('build_views')
        if req.form not in FORM_VIEW_PROFILES:
            raise OperationFailure('request.form_key_invalid')
        order = dict(req.indicator_order)
        long, banks, model = use_tables(invocation, (('long', req.long), ('banks', req.banks), ('model', req.model)), receipt=req.evidence, role='form_data', metadata=data_metadata(req.form, order, req.source_uses))
        if req.evidence is not None:
            for receipt in req.evidence.inputs:
                invocation.use(receipt)
        profile = FORM_VIEW_PROFILES[req.form]
        if not long.empty:
            date_col = next((name for name in ('date', 'Дата') if name in long), None)
            dates = long[date_col].nunique() if date_col is not None else 1
            invocation.budget.check('cells', len(order) * len(banks) * max(1, dates))
        sheets = build_form_sheets(profile=profile, df_long=long, df_banks=banks, model_df=model, indicator_order=order)
        evidence = record_tables(invocation, tuple(sheets.items()), metadata=views_metadata(req.form, profile, req.source_uses))
        return FormViews(req.form, profile, MappingProxyType(dict(sheets)), tuple(invocation.used_inputs), evidence, req.source_uses)
    return work(request, invocation)

def render_workbook(request: FormViews, *, style_registry=None, invocation=None) -> OperationResult[Representation]:

    def work(req, invocation):
        require_extra('pandas', 'dataframe')
        require_extra('openpyxl', 'excel')
        from dataclasses import asdict
        from stratbox.core.rendering.excel.api import active_styles
        from stratbox.core.rendering.excel.registry import BUILTIN_STYLES
        from stratbox.domains.cbr.products.reporting_forms.output import render_form_workbook
        invocation.stage('render')
        if not req.sheets:
            raise OperationFailure('request.empty_views')
        tables = tuple(req.sheets.items())
        frames = use_tables(invocation, tables, receipt=req.evidence, role='form_views', metadata=views_metadata(req.form, req.profile, req.source_uses))
        if req.evidence is not None:
            for receipt in req.evidence.inputs:
                invocation.use(receipt)
        sheets = dict(zip((name for name, _ in tables), frames, strict=True))
        selected = BUILTIN_STYLES if invocation.context.profile == 'managed' and style_registry is None else style_registry
        registry = active_styles(selected)
        result = Representation(f'cbr.forms.{req.profile}-xlsx', 1, XLSX, render_form_workbook(sheets, profile=req.profile, budget=invocation.budget, style_registry=registry))
        invocation.record(result.identity, parameters={'profile': req.profile, 'style': registry.default_preset_name, 'style_spec': asdict(registry.presets[registry.default_preset_name])})
        return result
    return work(request, invocation)


def capability_build_form_views(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.build_views', build_form_views)


def capability_render_workbook(values, invocation):
    from stratbox.domains.cbr.capability_methods import invoke_definition
    return invoke_definition(values, invocation, 'cbr.forms.render_workbook', render_workbook)
