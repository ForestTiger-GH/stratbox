"""
file_names — правила имени сохраняемого исходного файла Банка России.

Домен не меняет содержимое файла. На этом слое он только получает безопасное и
воспроизводимое имя для записи результата.
"""

from __future__ import annotations

import os
import re
import urllib.parse
from dataclasses import replace

from stratbox.macrobanks.cbr_file_collector.contracts import CbrDownloadedFileSource


def filename_from_headers(headers: dict[str, str] | None) -> str | None:
    if not headers:
        return None
    content_disposition = ""
    for key, value in headers.items():
        if str(key).lower() == "content-disposition":
            content_disposition = str(value)
            break
    if not content_disposition:
        return None

    match = re.search(r"filename\*=UTF-8''([^;]+)", content_disposition, flags=re.IGNORECASE)
    if match:
        return urllib.parse.unquote(match.group(1).strip().strip('"'))

    match = re.search(r'filename="?([^";]+)"?', content_disposition, flags=re.IGNORECASE)
    if match:
        return urllib.parse.unquote(match.group(1).strip())
    return None


def filename_from_url(url: str) -> str | None:
    parsed = urllib.parse.urlparse(str(url))
    raw_name = parsed.path.rsplit("/", 1)[-1].strip()
    if not raw_name:
        return None
    return urllib.parse.unquote(raw_name)


def sanitize_file_name(name: str, *, fallback: str = "downloaded_file") -> str:
    text = str(name or "").strip()
    text = text.replace("\\", "_").replace("/", "_")
    text = text.replace(":", "_").replace("*", "_")
    text = text.replace("?", "_").replace('"', "_")
    text = text.replace("<", "_").replace(">", "_").replace("|", "_")
    text = re.sub(r"\s+", " ", text).strip(" .")
    return text or fallback


def resolve_download_file_name(
    *,
    explicit_file_name: str | None,
    headers: dict[str, str] | None,
    url: str,
    fallback: str,
) -> str:
    candidate = explicit_file_name or filename_from_headers(headers) or filename_from_url(url) or fallback
    return sanitize_file_name(candidate, fallback=fallback)


def make_unique_file_name(file_name: str, used: set[str]) -> str:
    base = sanitize_file_name(file_name)
    key = base.lower()
    if key not in used:
        used.add(key)
        return base

    stem, ext = os.path.splitext(base)
    idx = 2
    while True:
        candidate = f"{stem}_{idx}{ext}"
        key = candidate.lower()
        if key not in used:
            used.add(key)
            return candidate
        idx += 1


def ensure_unique_download_file_names(files: list[CbrDownloadedFileSource]) -> list[CbrDownloadedFileSource]:
    used: set[str] = set()
    out: list[CbrDownloadedFileSource] = []
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
