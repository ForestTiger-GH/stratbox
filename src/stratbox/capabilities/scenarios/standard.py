"""Purposeful source-independent scenario definitions."""
from ..model import *
from ..operations.standard import EXTRACT_WORKBOOK, PUBLISH_PRODUCT, RELEASE
from ..commands.standard import P, DATASET

REFRESH = ScenarioDefinition('scenario.series.refresh', inputs={
    'material':P('material',required=False),'physical':P('physical',required=False),'issue':P('issue',required=False)},
    outputs={**EXTRACT_WORKBOOK.outputs,'reference':P('artifact',required=False),'product':P('product',required=False),'product_reference':P('artifact',required=False)},
    body=GraphBody((Call('extract','operation.series.extract_workbook',
        {'material':InputRef('material'),'physical':InputRef('physical'),'issue':InputRef('issue')}),),
        {'dataset':OutputRef('extract','dataset'),'assessment':OutputRef('extract','assessment')}), recipe=MethodRef('stratbox.capabilities.preparation.recipes.scenarios:refresh'))
ANALYSIS = ScenarioDefinition('scenario.analysis.prepare', inputs={'dataset':DATASET}, outputs={'dataset':DATASET},
    body=GraphBody((Call('validate','operation.observations.validate',{'dataset':InputRef('dataset')}),), {'dataset':OutputRef('validate','dataset')}), recipe=MethodRef('stratbox.capabilities.preparation.recipes.scenarios:analysis'))
# This purpose owns the complete publication obligation, separate from source refresh.
PUBLISH = ScenarioDefinition('scenario.release.publish',inputs=RELEASE.inputs,outputs=RELEASE.outputs,
    body=GraphBody((Call('release','operation.release.publish',{'members':InputRef('members'),'expected_token':InputRef('expected_token')}),),
        {'manifest':OutputRef('release','manifest'),'receipt':OutputRef('release','receipt')},required_completions=('release',)))
SCENARIOS=(REFRESH,ANALYSIS,PUBLISH)
