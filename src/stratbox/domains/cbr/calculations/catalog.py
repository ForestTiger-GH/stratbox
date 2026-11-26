"""Static numerical purposes, separate from publisher series and scheduling."""
from types import MappingProxyType
from stratbox.capabilities.model.domains import CalculationSpec, CommandSpec, Applicability
from stratbox.capabilities.model.methods import MethodRef
from stratbox.domains.cbr.series.reporting_forms import F101_TABLE, F102_TABLE, F123_TABLE, F134_TABLE, F135_TABLE, F802_TABLE, F803_TABLE, F805_TABLE
from stratbox.domains.cbr.common.contracts import FamilySettings

DEBT_APK = CalculationSpec("cbr.corporate_lending.debt_apk", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.industry.actions:calculate"),
        FamilySettings("cbr.corporate_lending.debt_0105a", "industry_debt")),
}))
ISSUANCE_APK = CalculationSpec("cbr.corporate_lending.issuance_apk", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.industry.actions:calculate"),
        FamilySettings("cbr.corporate_lending.issuance_0104a", "industry_issuance")),
}))

FORM_101 = CalculationSpec("cbr.forms.f101.model", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.reporting_forms.methods:calculate"), F101_TABLE),
}))
FORM_102 = CalculationSpec("cbr.forms.f102.model", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.reporting_forms.methods:calculate"), F102_TABLE),
}))
FORM_123 = CalculationSpec("cbr.forms.f123.model", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.reporting_forms.methods:calculate"), F123_TABLE),
}))
FORM_134 = CalculationSpec("cbr.forms.f134.model", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.reporting_forms.methods:calculate"), F134_TABLE),
}), semantics=MappingProxyType({"readiness": "requires_publisher_financial_model", "available": "published_field_observations"}))
FORM_135 = CalculationSpec("cbr.forms.f135.model", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.reporting_forms.methods:calculate"), F135_TABLE),
}))
FORM_802 = CalculationSpec("cbr.forms.f802.model", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.reporting_forms.methods:calculate"), F802_TABLE),
}))
FORM_803 = CalculationSpec("cbr.forms.f803.model", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.reporting_forms.methods:calculate"), F803_TABLE),
}), semantics=MappingProxyType({"readiness": "requires_publisher_financial_model", "available": "published_field_observations"}))
FORM_805 = CalculationSpec("cbr.forms.f805.model", MappingProxyType({
    "command.calculate.formula": CommandSpec(MethodRef("stratbox.domains.cbr.calculations.reporting_forms.methods:calculate"), F805_TABLE),
}))
