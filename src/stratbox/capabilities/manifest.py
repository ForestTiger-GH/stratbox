"""Single lightweight assembly point for the built-in typed capability catalog."""
from stratbox.capabilities.catalog import CatalogSnapshot, MethodDefinition, ProcessingGroup, RecipeDefinition
from stratbox.capabilities.commands import definitions as commands
from stratbox.capabilities.operations import definitions as operations, extraction_body
from stratbox.capabilities.scenarios import definitions as scenarios
from stratbox.capabilities.cascades import definitions as cascades
from stratbox.capabilities.commands.notifications import definitions as notification_commands
from stratbox.capabilities.operations.notifications import definitions as notification_operations


def catalog_snapshot():
    """Construct metadata without importing handlers or optional data backends."""
    return CatalogSnapshot(
        definitions=(*commands(), *notification_commands(), *operations(), *notification_operations(), *scenarios(), *cascades()),
        methods=(MethodDefinition("extract.rows", "extract.observations", extraction_body(), priority=1),
            MethodDefinition("extract.minfin_budget", "extract.observations",
                extraction_body("minfin.fields.interpret_budget"), group_ids=("minfin.budget.columns",))),
        groups=(ProcessingGroup("minfin.budget.columns", source_ids=("minfin.fedbud.annex3.monthly",),
            representations=("xlsx", "xlsm"), methods={"extract.observations": "extract.minfin_budget"}),),
        recipes=(RecipeDefinition("recipe.source_view", "source.view", "scenario.observation_view"),
            RecipeDefinition("recipe.ratio_product", "ratio.product", "scenario.observation_ratio"),
            RecipeDefinition("recipe.observation_package", "observation.package", "cascade.observation_package")),
    )
