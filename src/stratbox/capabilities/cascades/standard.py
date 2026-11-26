"""Bounded collections of independent scenario contracts."""
from ..model import *
from ..commands.standard import P
SOURCES=CascadeDefinition('cascade.sources.refresh',inputs={'members':P('members',tuple)},outputs={'results':P('result_collection',tuple)},
    body=GraphBody((MapCall('refresh','scenario.series.refresh',InputRef('members'),item_input='material',output_port='dataset'),),{'results':OutputRef('refresh','items')}))
ANALYSIS=CascadeDefinition('cascade.analysis.release',inputs={'members':P('members',tuple)},outputs={'results':P('result_collection',tuple)},
    body=GraphBody((MapCall('prepare','scenario.analysis.prepare',InputRef('members'),item_input='dataset'),),{'results':OutputRef('prepare','items')}))
CASCADES=(SOURCES,ANALYSIS)
