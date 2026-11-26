"""Explicit assembly of the standard catalog and static domain records."""
from __future__ import annotations

from hashlib import sha256
from importlib import resources


def implementation_identity() -> str:
    """Fingerprint the actual packaged code and rules, including development trees."""
    from stratbox import __version__
    digest = sha256()
    def visit(directory, prefix=''):
        for entry in sorted(directory.iterdir(), key=lambda item: item.name):
            name = prefix + entry.name
            if entry.name.startswith('.') or entry.name == '__pycache__':
                continue
            if entry.is_dir():
                visit(entry, name + '/')
            elif entry.name.endswith(('.py', '.json', '.csv', '.xml')):
                data = entry.read_bytes()
                digest.update(name.encode('utf-8') + b'\0')
                digest.update(sha256(data).digest())
    visit(resources.files('stratbox'))
    return 'stratbox:' + __version__ + ':' + digest.hexdigest()


def default_catalog():
    from stratbox.capabilities.catalog import standard_catalog
    return standard_catalog()


def default_domains():
    from stratbox.capabilities.catalog.domains import load_domains
    return load_domains()
