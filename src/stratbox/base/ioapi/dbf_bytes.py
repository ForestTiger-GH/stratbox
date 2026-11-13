"""Open exact DBF bytes using a format decoder that requires a local path."""

from contextlib import contextmanager
from struct import unpack_from

from stratbox.base.filestore import workdir
from stratbox.base.utils.optional_deps import require_extra


@contextmanager
def open_dbf_bytes(data: bytes, *, budget=None, **options):
    if len(data) < 33:
        raise ValueError("DBF header is truncated")
    count, header, width = unpack_from("<IHH", data, 4)
    if not 33 <= header <= len(data) or not width or count * width > len(data) - header:
        raise ValueError("DBF record geometry is invalid")
    if budget is not None:
        budget.charge("temporary_bytes", len(data))
    dbfread = require_extra("dbfread", "dbf")
    with workdir("stratbox-dbf-") as directory:
        path = directory / "source.dbf"
        path.write_bytes(data)
        yield dbfread.DBF(str(path), ignore_missing_memofile=True, **options)
