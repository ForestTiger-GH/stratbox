"""One content identity for packaged implementation code and scientific rules."""
from hashlib import sha256
from importlib import resources


def implementation_identity():
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
                digest.update(name.encode('utf-8') + b'\0')
                digest.update(sha256(entry.read_bytes()).digest())

    visit(resources.files('stratbox'))
    return 'stratbox:' + __version__ + ':' + digest.hexdigest()
