"""Execution facades for direct domain methods."""
from __future__ import annotations
import stratbox.domains.cbr.methods.collection.handlers as _methods
from stratbox.domains.cbr.methods.collection.handlers import *
from stratbox.core.execution import run
from stratbox.operations.declarations import definition as _definition

def __getattr__(name):
    return getattr(_methods, name)

def discover(request: DiscoverFilesRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.file_collector.discover'), request, lambda req, invocation: _methods.discover(req, invocation=invocation), context=context)

def collect_raw(request: CollectFilesRequest, *, transport: HttpTransport | None=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.file_collector.collect_raw'), request, lambda req, invocation: _methods.collect_raw(req, invocation=invocation, transport=transport), context=context, providers={'http': transport})

def collect_to_store(request: CollectToStoreRequest, *, transport: StreamingHttpTransport | None=None, store=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.file_collector.collect_to_store'), request, lambda req, invocation: _methods.collect_to_store(req, invocation=invocation, transport=transport, store=store), context=context, providers={'http': transport, 'output_filestore': store})

def prepare_archive(request: PrepareArchiveRequest, *, context: ExecutionContext | None=None):
    return run(_definition('cbr.file_collector.prepare_archive'), request, lambda req, invocation: _methods.prepare_archive(req, invocation=invocation), context=context)

def archive_to_store(request: StoreArchiveRequest, *, source_store=None, output_store=None, context: ExecutionContext | None=None):
    return run(_definition('cbr.file_collector.archive_to_store'), request, lambda req, invocation: _methods.archive_to_store(req, invocation=invocation, source_store=source_store, output_store=output_store), context=context, providers={'filestore': source_store, 'output_filestore': output_store})
