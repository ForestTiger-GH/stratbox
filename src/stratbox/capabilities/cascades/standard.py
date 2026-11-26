"""Bounded collections of independent scenario contracts."""
from ..model import *
from ..commands.standard import P
SOURCES=CascadeDefinition('cascade.sources.refresh',inputs={'members':P('members',tuple)},outputs={'results':P('result_collection',tuple),'outcomes':P('unit_outcomes',tuple)},
    body=GraphBody((MapCall('refresh','scenario.series.refresh',InputRef('members'),item_input='material',output_port='dataset'),),{'results':OutputRef('refresh','items'),'outcomes':OutputRef('refresh','outcomes')}), recipe=MethodRef('stratbox.capabilities.preparation.recipes.cascades:sources_refresh'))
ANALYSIS=CascadeDefinition('cascade.analysis.release',inputs={'members':P('members',tuple),
    'member_destination':P('destination',required=False),'expected_token':P('state_token',required=False)},
    outputs={'results':P('result_collection',tuple),'outcomes':P('unit_outcomes',tuple),
             'manifest':P('release_manifest'),'receipt':P('publication_receipt')},
    body=GraphBody((MapCall('prepare','scenario.analysis.prepare',InputRef('members'),item_input='dataset',
        inputs={'destination':InputRef('member_destination')},parameters={'product':True},output_port='reference'),
        Call('publish','scenario.release.publish',{'members':OutputRef('prepare','items'),'expected_token':InputRef('expected_token')})),
        {'results':OutputRef('prepare','items'),'outcomes':OutputRef('prepare','outcomes'),
         'manifest':OutputRef('publish','manifest'),'receipt':OutputRef('publish','receipt')},required_completions=('publish',)), recipe=MethodRef('stratbox.capabilities.preparation.recipes.cascades:analysis_release'))
CASCADES=(SOURCES,ANALYSIS)
