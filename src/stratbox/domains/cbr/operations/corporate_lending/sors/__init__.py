"""Typed corporate lending operation API; implementations load on demand."""
from importlib import import_module

_EXPORTS = {'CROSSWALK': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions', 'CROSSWALK'),
 'CrosswalkSorsRequest': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                          'CrosswalkSorsRequest'),
 'DEPENDENCIES': ('stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies',
                  'DEPENDENCIES'),
 'LOAD': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions', 'LOAD'),
 'PIVOT': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions', 'PIVOT'),
 'PREPARE': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions', 'PREPARE'),
 'PREPARE_FROM_FLAKES': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                         'PREPARE_FROM_FLAKES'),
 'PivotSorsRequest': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                      'PivotSorsRequest'),
 'PrepareSorsOriginalsRequest': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                                 'PrepareSorsOriginalsRequest'),
 'READ': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions', 'READ'),
 'READ_VIEW_SNAPSHOT': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                        'READ_VIEW_SNAPSHOT'),
 'RENDER': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions', 'RENDER'),
 'RESTORE': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions', 'RESTORE'),
 'RESTORE_FROM_ORIGINALS': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                            'RESTORE_FROM_ORIGINALS'),
 'ReadSorsSnapshotRequest': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                             'ReadSorsSnapshotRequest'),
 'RenderSorsRequest': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                       'RenderSorsRequest'),
 'RestoreSorsRequest': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                        'RestoreSorsRequest'),
 'SorsBundleSnapshotRequest': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                               'SorsBundleSnapshotRequest'),
 'SorsCrosswalkConfig': ('stratbox.domains.cbr.analytics.corporate_lending.sors.contracts',
                         'SorsCrosswalkConfig'),
 'SorsCrosswalkResult': ('stratbox.domains.cbr.analytics.corporate_lending.sors.results',
                         'SorsCrosswalkResult'),
 'SorsCrosswalkSnapshotRequest': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                                  'SorsCrosswalkSnapshotRequest'),
 'SorsDependency': ('stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.dependencies',
                    'SorsDependency'),
 'SorsDeterministicConfig': ('stratbox.domains.cbr.analytics.corporate_lending.sors.contracts',
                             'SorsDeterministicConfig'),
 'SorsOptimizationConfig': ('stratbox.domains.cbr.analytics.corporate_lending.sors.contracts',
                            'SorsOptimizationConfig'),
 'SorsPivotRequest': ('stratbox.domains.cbr.products.corporate_lending.sors.contracts', 'SorsPivotRequest'),
 'SorsPivotResult': ('stratbox.domains.cbr.products.corporate_lending.sors.results', 'SorsPivotResult'),
 'SorsRestorationResult': ('stratbox.domains.cbr.analytics.corporate_lending.sors.results',
                           'SorsRestorationResult'),
 'SorsRestorationSnapshotRequest': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions',
                                    'SorsRestorationSnapshotRequest'),
 'SorsRunConfig': ('stratbox.domains.cbr.analytics.corporate_lending.sors.contracts', 'SorsRunConfig'),
 'SorsRunSummary': ('stratbox.domains.cbr.analytics.corporate_lending.sors.results', 'SorsRunSummary'),
 'SorsSelectionPolicy': ('stratbox.domains.cbr.analytics.corporate_lending.sors.contracts',
                         'SorsSelectionPolicy'),
 'SorsSourceBundle': ('stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts',
                      'SorsSourceBundle'),
 'SorsSourceFiles': ('stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts',
                     'SorsSourceFiles'),
 'SorsSourceInputs': ('stratbox.domains.cbr.analytics.corporate_lending.sors.inputs.contracts',
                      'SorsSourceInputs'),
 'SorsTargetScope': ('stratbox.domains.cbr.analytics.corporate_lending.sors.contracts', 'SorsTargetScope'),
 'SorsViewPack': ('stratbox.domains.cbr.products.corporate_lending.sors.results', 'SorsViewPack'),
 'SorsWorkbookRequest': ('stratbox.domains.cbr.products.corporate_lending.sors.contracts',
                         'SorsWorkbookRequest'),
 'SorsWorkbookResult': ('stratbox.domains.cbr.products.corporate_lending.sors.results', 'SorsWorkbookResult'),
 'VIEWS': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions', 'VIEWS'),
 'VIEW_SNAPSHOT': ('stratbox.domains.cbr.operations.corporate_lending.sors.definitions', 'VIEW_SNAPSHOT'),
 'build_bundle_snapshot': ('stratbox.domains.cbr.operations.corporate_lending.sors.snapshot_operations',
                           'build_bundle_snapshot'),
 'build_crosswalk_snapshot': ('stratbox.domains.cbr.operations.corporate_lending.sors.snapshot_operations',
                              'build_crosswalk_snapshot'),
 'build_pivot': ('stratbox.domains.cbr.operations.corporate_lending.sors.api', 'build_pivot'),
 'build_restoration_snapshot': ('stratbox.domains.cbr.operations.corporate_lending.sors.snapshot_operations',
                                'build_restoration_snapshot'),
 'prepare_from_originals': ('stratbox.domains.cbr.operations.corporate_lending.sors.api',
                            'prepare_from_originals'),
 'read_bundle_snapshot': ('stratbox.domains.cbr.operations.corporate_lending.sors.snapshot_operations',
                          'read_bundle_snapshot'),
 'read_crosswalk_snapshot': ('stratbox.domains.cbr.operations.corporate_lending.sors.snapshot_operations',
                             'read_crosswalk_snapshot'),
 'read_restoration_snapshot': ('stratbox.domains.cbr.operations.corporate_lending.sors.snapshot_operations',
                               'read_restoration_snapshot'),
 'read_source_files': ('stratbox.domains.cbr.operations.corporate_lending.sors.api', 'read_source_files'),
 'render_views': ('stratbox.domains.cbr.operations.corporate_lending.sors.api', 'render_views'),
 'restore': ('stratbox.domains.cbr.operations.corporate_lending.sors.api', 'restore'),
 'run_crosswalk': ('stratbox.domains.cbr.operations.corporate_lending.sors.api', 'run_crosswalk')}
__all__ = tuple(_EXPORTS)

def __getattr__(name):
    target = _EXPORTS.get(name)
    if target is None:
        raise AttributeError(name)
    module, symbol = target
    value = getattr(import_module(module), symbol)
    globals()[name] = value
    return value

_EXPORTS.update({name: ("stratbox.domains.cbr.operations.corporate_lending.sors.api", name)
                 for name in ("prepare_inputs", "prepare_from_flakes", "restore_from_originals", "build_views")})
_EXPORTS.update({name: ("stratbox.domains.cbr.operations.corporate_lending.sors.definitions", name)
                 for name in ("PrepareSorsRequest", "PrepareSorsFlakesRequest", "RestoreSorsOriginalsRequest", "BuildSorsViewsRequest", "SorsViewSnapshotRequest")})
_EXPORTS.update({name: ("stratbox.domains.cbr.operations.corporate_lending.sors.snapshot_operations", name)
                 for name in ("build_view_snapshot", "read_view_snapshot")})
__all__ = tuple(_EXPORTS)
