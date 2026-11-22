"""Explicit adapter selection for distributed, pinned dataset components."""

from .ports import DatasetReader, DatasetStorageError
from stratbox.shared.data.snapshots import SnapshotReference


class DatasetProviders:
    def __init__(self, providers: tuple[DatasetReader, ...]):
        self._providers = {}
        for provider in providers:
            key = (provider.provider_id, provider.scope_id)
            if key in self._providers:
                raise DatasetStorageError("dataset.provider_conflict")
            self._providers[key] = provider

    def resolve(self, reference: SnapshotReference) -> DatasetReader:
        try:
            return self._providers[(reference.provider_id, reference.scope_id)]
        except KeyError:
            raise DatasetStorageError("dataset.provider_unavailable") from None
