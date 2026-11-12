"""Open exact DBF bytes using a format decoder that requires a local path."""

from contextlib import contextmanager

from stratbox.base.filestore import workdir
from stratbox.base.utils.optional_deps import require_extra


@contextmanager
def open_dbf_bytes(data: bytes, **options):
    dbfread = require_extra("dbfread", "dbf")
    with workdir("stratbox-dbf-") as directory:
        path = directory / "source.dbf"
        path.write_bytes(data)
        yield dbfread.DBF(str(path), ignore_missing_memofile=True, **options)
