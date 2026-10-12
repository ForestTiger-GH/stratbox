#!/usr/bin/env python3
"""Verify both committed link-detachment batches changed only hyperlink syntax.

This tests the two exact Git migration transitions. It does not imply
independent original Research-to-Science semantic preservation.
"""
from __future__ import annotations
import json
import re
import subprocess
from pathlib import Path
from urllib.parse import unquote, urlsplit
from migrate_knowledge_research_links import INLINE_LINK, forbidden

ROOT=Path(__file__).resolve().parents[4]
FIRST_BEFORE="7deed98376092c1002090a5b5361de7ae6290f9f"
FIRST_AFTER="9008b1388da2317dc69537bbcacd7ac9f93ed043"
SECOND_BEFORE="f238e38879121edc28de9541aaa46c821952c032"
SECOND_AFTER="ae02bbeb2895dcba94bb99dec607e5fe89759572"

def git(*args: str)->str:
    return subprocess.check_output(["git",*args],cwd=ROOT).decode("utf-8")

def content(version:str,path:str)->str:
    return git("show",f"{version}:{path}")

def first_transform(text:str)->str:
    marker=chr(92)+chr(96)
    def replace(m:re.Match[str])->str:
        label,target=m.groups()
        if not forbidden(target):
            return m.group(0)
        fragment=unquote(urlsplit(target.strip()).fragment)
        span=re.search(r"L\d+(?:-L\d+)?",fragment)
        if span:
            label_token="#"+span.group(0)
            if label_token not in label:
                return f"{label} ({marker}{label_token}{marker})"
        return label
    return INLINE_LINK.sub(replace,text)

def second_transform(text:str)->str:
    processed=INLINE_LINK.sub(lambda m: m.group(1) if forbidden(m.group(2)) else m.group(0),text)
    marker=chr(92)+chr(96)
    pattern=re.compile(re.escape(marker)+r"(#L\d+(?:-L\d+)?)"+re.escape(marker))
    return pattern.sub(lambda m: f"{chr(96)}{m.group(1)}{chr(96)}",processed)

def changed(start:str,end:str)->list[str]:
    return [s for s in git("diff","--name-only",start,end,"--","docs/").splitlines() if s.endswith(".md")]

def verify()->dict:
    first=changed(FIRST_BEFORE,FIRST_AFTER)
    second=changed(SECOND_BEFORE,SECOND_AFTER)
    issues=[]
    for path in first:
        if first_transform(content(FIRST_BEFORE,path))!=content(FIRST_AFTER,path):
            issues.append("unexpected change in first batch: "+path)
    for path in second:
        if second_transform(content(SECOND_BEFORE,path))!=content(SECOND_AFTER,path):
            issues.append("unexpected change in second batch: "+path)
    result={"verdict":"EXACT_MARKDOWN_LINK_DETACHMENT_FIDELITY_ONLY","first_batch_files":len(first),"second_batch_files":len(second),"unexpected_text_changes":len(issues),"independent_research_semantics":"NOT_CERTIFIED"}
    print(json.dumps(result,ensure_ascii=False))
    for issue in issues[:30]:
        print("FAIL",issue)
    if issues:
        raise SystemExit(1)
    return result

if __name__=="__main__":
    verify()
