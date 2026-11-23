"""Reporting-form sources are independent of financial-model coverage."""
from stratbox.domains.cbr.publications.catalog import all_sources

def source_forms():
    return all_sources("cbr.reporting_forms")
