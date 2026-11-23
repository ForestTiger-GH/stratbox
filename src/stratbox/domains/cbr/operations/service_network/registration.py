"""Operation segment projected from the packaged registry."""
from stratbox.core.registry.operations import operation_references

OPERATIONS = operation_references("cbr", handler_module='stratbox.domains.cbr.operations.service_network')
