"""Catalog descriptions are read-only projections of existing registrations."""

from stratbox.core.registry.operations import definition as _registry_definition
from stratbox.shared.data.processing import DataContract
from .contracts import DescribeSourceRequest, DescribeFamilyRequest, SourceDescription, FamilyDescription

DESCRIBE_SOURCE = _registry_definition('cbr.describe_source')
DESCRIBE_FAMILY = _registry_definition('cbr.describe_family')
