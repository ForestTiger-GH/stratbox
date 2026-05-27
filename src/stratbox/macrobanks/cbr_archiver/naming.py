"""
naming — правила именования файлов в домене cbr_archiver.

Имена файлов определяются без изменения содержимого файлов:
- сначала используется имя из HTTP-заголовков;
- затем последний сегмент URL;
- явное имя возможно только для пользовательского CbrArchiveSource;
- при конфликте имена безопасно уникализируются.
"""

from __future__ import annotations

import re
from dataclasses import replace
from posixpath import basename as posix_basename
from urllib.parse import unquote, urlsplit

from stratbox.macrobanks.cbr_archiver.models import CbrDownloadedFile


def filename_from_headers(headers: dict[str, str] | None) -> str | None:
    """Извлекает имя файла из Content-Disposition, если сервер его передал."""
    if not headers:
        return None

    lower_headers = {str(k).lower(): str(v) for k, v in headers.items()}
    content_disposition = lower_headers.get("content-disposition", "")
    if not content_disposition:
        return None

    match = re.search(r"filename\*?=(?:UTF-8''|utf-8'')?\"?([^\";]+)\"?", content_disposition)
    if not match:
        return None

    raw_name = match.group(1).strip()
    return sanitize_file_name(unquote(raw_name)) or None


def filename_from_url(url: str, fallback: str = "downloaded_file.xlsx") -> str:
    """Возвращает имя файла из последнего сегмента URL."""
    path = urlsplit(str(url)).path or ""
    name = posix_basename(path)
    name = unquote(name)
    return sanitize_file_name(name) or fallback


def resolve_download_file_name(
    *,
    explicit_file_name: str | None,
    headers: dict[str, str] | None,
    url: str,
    fallback: str = "downloaded_file.xlsx",
) -> str:
    """Определяет итоговое имя скачанного файла."""
    if explicit_file_name:
        return sanitize_file_name(explicit_file_name) or fallback

    from_headers = filename_from_headers(headers)
    if from_headers:
        return from_headers

    return filename_from_url(url, fallback=fallback)


def sanitize_file_name(name: str) -> str:
    """Приводит имя файла к безопасному виду без каталогов и управляющих символов."""
    text = str(name or "").strip().replace("\\", "/")
    text = text.split("/")[-1].strip()
    text = re.sub(r"[\x00-\x1f\x7f]", "", text)
    text = re.sub(r'[<>:"|?*]', "_", text)
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text


def make_unique_file_name(file_name: str, used: set[str]) -> str:
    """Возвращает уникальное имя файла, не конфликтующее с уже использованными."""
    safe_name = sanitize_file_name(file_name) or "downloaded_file.xlsx"
    key = safe_name.lower()
    if key not in used:
        used.add(key)
        return safe_name

    if "." in safe_name:
        stem, ext = safe_name.rsplit(".", 1)
        ext = f".{ext}"
    else:
        stem, ext = safe_name, ""

    idx = 2
    while True:
        candidate = f"{stem}_{idx}{ext}"
        key = candidate.lower()
        if key not in used:
            used.add(key)
            return candidate
        idx += 1


def ensure_unique_download_file_names(files: list[CbrDownloadedFile]) -> list[CbrDownloadedFile]:
    """Уникализирует имена скачанных файлов в пределах одного запуска."""
    used: set[str] = set()
    out: list[CbrDownloadedFile] = []
    for item in files:
        unique_name = make_unique_file_name(item.file_name, used)
        if unique_name == item.file_name:
            out.append(item)
        else:
            out.append(replace(item, file_name=unique_name))
    return out


__all__ = [
    "ensure_unique_download_file_names",
    "filename_from_headers",
    "filename_from_url",
    "make_unique_file_name",
    "resolve_download_file_name",
    "sanitize_file_name",
]
