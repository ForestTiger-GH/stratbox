#!/usr/bin/env python3
"""Build and verify a reproducible Knowledge-only ZIP for archive-deletion rehearsal.

The ZIP includes only maintained docs/ files and a content hash manifest.
It deliberately excludes _mw, Research, docs_old, repository source and runtime
state. Success means portable bytes/navigation, NOT semantic lossless assurance.
"""
from __future__ import annotations
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile
from pathlib import Path
from urllib.parse import unquote, urlsplit

ROOT=Path(__file__).resolve().parents[4]
DOCS=ROOT/"docs"
OUTPUT=ROOT/"dist/strategy-box-knowledge-standalone.zip"
SHAFILE=ROOT/"dist/strategy-box-knowledge-standalone.sha256"
ZIP_TIME=(1980,1,1,0,0,0)
LINK=re.compile(r"\[([^\]\n]+)\]\(([^)\n]+)\)")
BANNED={"_mw","docs_old","research"}

def digest(x:bytes)->str:
    return hashlib.sha256(x).hexdigest()

def git_head()->str:
    return subprocess.check_output(["git","rev-parse","HEAD"],cwd=ROOT,text=True).strip()

def info(name:str)->zipfile.ZipInfo:
    z=zipfile.ZipInfo(name,ZIP_TIME)
    z.compress_type=zipfile.ZIP_DEFLATED
    z.create_system=3
    z.external_attr=(0o100644 << 16)
    z.flag_bits=0
    return z

def verify_extracted(folder:Path, expected:dict)->dict:
    files=sorted((folder/"docs").rglob("*"))
    assert not any(p.is_symlink() for p in files)
    relative=[p.relative_to(folder).as_posix() for p in files if p.is_file()]
    assert relative==sorted(expected),("unexpected/missing files",set(relative)^set(expected))
    assert all(digest((folder/p).read_bytes())==expected[p] for p in relative)
    links=0
    for name in relative:
        if not name.endswith(".md"):
            continue
        file=folder/name
        content=file.read_text(encoding="utf-8")
        for label,target in LINK.findall(content):
            parsed=urlsplit(unquote(target.strip()))
            if parsed.scheme or parsed.netloc or target.startswith("#") or not parsed.path:
                continue
            links+=1
            dest=(file.parent/parsed.path).resolve()
            assert dest.is_relative_to((folder/"docs").resolve()),(name,target)
            assert dest.exists(),(name,target)
        for m in re.finditer(r"https?://[^\s)>\"']+",content):
            value=unquote(m.group(0))
            parsed=urlsplit(value)
            parts={x.lower() for x in parsed.path.split("/") if x}
            if parsed.netloc.lower() in {"github.com","raw.githubusercontent.com"} and "_mw" in parts:
                raise AssertionError("source-work URL in published Knowledge: "+name)
    return {"docs_files":len(relative),"markdown_files":sum(x.endswith(".md") for x in relative),"internal_links_verified":links}

def main()->None:
    paths=sorted(p for p in DOCS.rglob("*") if p.is_file())
    assert paths and all(not p.is_symlink() for p in paths)
    listed={p.relative_to(ROOT).as_posix():digest(p.read_bytes()) for p in paths}
    assert all(p.split("/",1)[0]=="docs" for p in listed)
    assert all(not BANNED.intersection(p.lower().split("/")) for p in listed)
    manifest={
        "edition":"STRATEGY_BOX_KNOWLEDGE_ONLY_PARTIAL",
        "git_commit":git_head(),
        "files_sha256":listed,
        "assurance_scope":"NAVIGATION_AND_CONTENT_INTEGRITY_ONLY",
        "independent_research_semantic_assurance":"OPEN",
        "original_annotated_docx":"LOST_BY_OWNER_EXCLUDED",
        "deployed_product_conformance":"NOT_CERTIFIED",
    }
    OUTPUT.parent.mkdir(parents=True,exist_ok=True)
    with zipfile.ZipFile(OUTPUT,"w") as z:
        z.writestr(info("KNOWLEDGE-HASHES.json"),(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+"\n").encode("utf-8"),compresslevel=9)
        for name in sorted(listed):
            z.writestr(info(name),(ROOT/name).read_bytes(),compresslevel=9)
    with tempfile.TemporaryDirectory(prefix="strategy-box-knowledge-amputation-") as td:
        folder=Path(td)
        with zipfile.ZipFile(OUTPUT,"r") as z:
            members=z.namelist()
            assert members==["KNOWLEDGE-HASHES.json",*sorted(listed)]
            assert all(not BANNED.intersection(v.lower().split("/")) for v in members)
            z.extractall(folder)
        imported=json.loads((folder/"KNOWLEDGE-HASHES.json").read_text(encoding="utf-8"))
        assert imported==manifest
        proof=verify_extracted(folder,listed)
    SHA= digest(OUTPUT.read_bytes())
    SHAFILE.write_text(SHA+"  "+OUTPUT.name+"\n",encoding="utf-8")
    print(json.dumps({
        "verdict":"REPRODUCIBLE_SOURCE_ARCHIVE_FREE_KNOWLEDGE_ZIP",
        "zip_sha256":SHA,
        "zip_bytes":OUTPUT.stat().st_size,
        "git_commit":manifest["git_commit"],
        "docs_files":proof["docs_files"],
        "markdown_files":proof["markdown_files"],
        "relative_links_checked":proof["internal_links_verified"],
        "original_research_work_legacy_present":False,
        "independent_semantic_assurance":"OPEN",
    },ensure_ascii=False))

if __name__=="__main__":
    main()
