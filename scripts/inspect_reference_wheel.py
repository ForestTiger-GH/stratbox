"""Compare exact final package code/resources in wheel or sdist, without executing it."""
from __future__ import annotations

import argparse
from hashlib import sha256
from pathlib import Path, PurePosixPath
import tarfile
from zipfile import ZipFile

ROOT = Path(__file__).resolve().parents[1]
PACKAGE = ROOT / 'src' / 'stratbox'
RETIRED = ('operations/', 'composition/', 'domains/registry/', 'core/operations/', 'core/capabilities/')
def package_asset(path):
    relative = PurePosixPath(path)
    return (not any(part.startswith('.') or part == '__pycache__' for part in relative.parts)
            and relative.suffix not in {'.md', '.pyc', '.pyo'})


def inventory(package=PACKAGE):
    return {path.relative_to(package).as_posix(): sha256(path.read_bytes()).hexdigest()
            for path in package.rglob('*') if path.is_file() and package_asset(path.relative_to(package).as_posix())}


def inspect_archive(archive: Path, *, source=PACKAGE):
    if archive.suffix == '.whl':
        owner = ZipFile(archive)
        names = owner.namelist()
        regular = {member.filename for member in owner.infolist() if not member.is_dir()}
        unsupported = set()
        reader = owner.read
        marker = 'stratbox/'
        prefix = marker
    else:
        owner = tarfile.open(archive, 'r:*')
        names = owner.getnames()
        regular = {member.name for member in owner.getmembers() if member.isfile()}
        unsupported = {member.name for member in owner.getmembers() if not member.isfile() and not member.isdir()}
        candidates = [name[:-len('src/stratbox/__init__.py')] for name in names if name.endswith('src/stratbox/__init__.py')]
        if len(candidates) != 1:
            owner.close()
            raise ValueError('archive.package_root_ambiguous')
        prefix = candidates[0] + 'src/stratbox/'
        def reader(name):
            handle = owner.extractfile(name)
            if handle is None:
                raise ValueError('archive.member_not_file:' + name)
            return handle.read()
    try:
        actual = {name[len(prefix):] for name in regular if name.startswith(prefix)
                  and PurePosixPath(name).suffix != '.md' and not name.endswith('/')}
        unsupported = {name for name in unsupported if name.startswith(prefix)}
        duplicates = len([name for name in names if name.startswith(prefix)]) != len({name for name in names if name.startswith(prefix)})
        expected = inventory(source)
        missing = expected.keys() - actual
        extra = actual - expected.keys()
        changed = {name for name in expected.keys() & actual if sha256(reader(prefix + name)).hexdigest() != expected[name]}
        retired = {name for name in actual if name.startswith(RETIRED) or name.endswith('/profiles.py')}
        if missing or extra or changed or retired or duplicates or unsupported:
            raise ValueError(f'archive.mismatch missing={sorted(missing)} extra={sorted(extra)} changed={sorted(changed)} retired={sorted(retired)} duplicates={duplicates} unsupported={sorted(unsupported)}')
        return {'members':len(actual),'resources':sum(not n.endswith(('.py','.pyi')) for n in actual)}
    finally:
        owner.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    result = inspect_archive(parser.parse_args().archive)
    print('Package archive verified:', result)


if __name__ == '__main__':
    main()
