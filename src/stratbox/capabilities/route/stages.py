"""The reference route is a capability map, not a mandatory ladder."""
from ..model import freeze
STAGES = freeze({
    'locate': ('command.request.prepare', 'command.issue.select'),
    'inspect': ('command.publication.scan', 'command.source.assess'),
    'acquire': ('command.material.fetch', 'command.material.read'),
    'decode': ('command.workbook.decode', 'command.document.decode', 'command.json.decode', 'command.csv.decode', 'command.dbf.decode', 'command.archive.unpack'),
    'readable': ('command.publication.transcribe',),
    'extract': ('command.table.extract', 'command.table.interpret', 'command.observations.validate'),
    'align': ('command.observations.align',),
    'calculate': ('command.calculate.change', 'command.calculate.ratio', 'command.calculate.formula', 'command.calculate.index', 'command.calculate.flow', 'command.timeseries.adjust', 'command.constraints.build'),
    'prepare': ('command.view.prepare',), 'render': ('command.product.render',),
    'retain': ('command.artifact.commit', 'command.dataset.ingest'),
    'release': ('command.release.assemble', 'command.release.publish'),
})
