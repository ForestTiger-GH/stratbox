#!/usr/bin/env python3
"""Structural owner-consistency of fifteen published cross-surface fault families."""
from pathlib import Path
import re,json
ROOT=Path(__file__).resolve().parents[4]
F=ROOT/"docs/science/engineering/cross-surface-failure-equivalence-and-proof-boundaries.md"
OWNERS={"SEC":ROOT/"docs/ldd/security/scoped-authority-and-privacy-vectors.md","MAC":ROOT/"docs/ldd/capabilities/machine-operation-adapter-conformance.md","OBS":ROOT/"docs/ldd/observability/execution-truth-and-recovery-vectors.md","PR":ROOT/"docs/ldd/data/used-source-receipt-boundary.md"}
def verify():
    text=F.read_text(encoding="utf-8")
    matches=re.findall(r"(?m)^\| F-(\d\d) \|",text)
    assert matches==[f"{i:02d}" for i in range(1,16)]
    links=re.findall(r"\[`((?:SEC|MAC|OBS|PR)-\d\d)`\]\(([^)]+)\)",text)
    assert len(links)>=50
    seen=set()
    for ident,dest in links:
        prefix=ident.split("-")[0]
        owner=OWNERS[prefix]
        assert (F.parent/dest).resolve()==owner.resolve(),(ident,dest)
        assert f"| {ident} |" in owner.read_text(encoding="utf-8"),ident
        seen.add(ident)
    assert len(seen)>=40
    for p in OWNERS.values():
        assert p.is_file()
    print(json.dumps({"verdict":"CROSS_CASE_OWNER_REF_INDEPENDENCE_ONLY","families":len(matches),"distinct_referenced_vectors":len(seen),"links":len(links),"executed_host_tests":0,"independent_semantic_review":"OPEN"}))
if __name__=="__main__":verify()
