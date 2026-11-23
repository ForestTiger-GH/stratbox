"""Validate canonical operation owners against importable domain packages."""
from stratbox.core.resources import owner_directories


class DomainLayoutError(ValueError):
    """A declared implementation owner is unreachable as a Python package."""


def discover_operation_owners(directory, *, declarations=None):
    if not directory.joinpath('__init__.py').is_file():
        raise DomainLayoutError('domain.root_not_package')
    owners = []
    for owner, _ in owner_directories(root=declarations):
        if owner.startswith('core.'):
            continue
        current = directory
        for component in owner.split('.'):
            current = current.joinpath(component)
            if not current.joinpath('__init__.py').is_file():
                raise DomainLayoutError('domain.unreachable_owner:' + owner)
        owners.append(owner)
    return tuple(sorted(owners))
