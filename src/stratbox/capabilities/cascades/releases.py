"""Independent retained products and coherent product member publication."""
from stratbox.capabilities.catalog import CatalogContribution, RecipeDefinition
from stratbox.capabilities.model import CapabilityRef
from stratbox.capabilities.scenarios.workflows import ScenarioMember, cascade_definition


def contribution(snapshot):
    products = cascade_definition(snapshot, 'cascade.retained_products', (
        ScenarioMember('primary', CapabilityRef('scenario.retained_product')),
        ScenarioMember('secondary', CapabilityRef('scenario.retained_product'))))
    release = cascade_definition(snapshot, 'cascade.coherent_products', (
        ScenarioMember('primary', CapabilityRef('scenario.save_retained_product')),
        ScenarioMember('secondary', CapabilityRef('scenario.save_retained_product'))), coherent=True)
    return CatalogContribution(definitions=(products, release), recipes=(
        RecipeDefinition('recipe.retained_products', 'retained.products', products.id),
        RecipeDefinition('recipe.coherent_products', 'retained.products.save', release.id)))
