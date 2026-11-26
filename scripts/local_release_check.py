"""Local structural, behavioral and installed-distribution acceptance; no remote workflows."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def check(report_path: Path, *, full_pytest=True):
    report={'started_at':datetime.now(timezone.utc).isoformat(),'steps':[],'result':'incomplete'}
    def run(name,args,cwd=ROOT):
        process=subprocess.run(args,cwd=cwd,check=False)
        report['steps'].append({'name':name,'exit_code':process.returncode})
        if process.returncode:
            raise RuntimeError(name+' failed')
    try:
        for name in ('check_release_integrity','check_internal_imports','check_readme_links'):
            run(name,[sys.executable,'-B','scripts/'+name+'.py'])
        if full_pytest:
            run('pytest',[sys.executable,'-B','-m','pytest','-q'])
        with tempfile.TemporaryDirectory(prefix='stratbox-release-') as temporary:
            directory=Path(temporary)
            dist=directory/'dist'
            run('build',[sys.executable,'-B','-m','build','--no-isolation','--outdir',str(dist)])
            wheels=list(dist.glob('*.whl'));sources=list(dist.glob('*.tar.gz'))
            if len(wheels)!=1 or len(sources)!=1:
                raise RuntimeError('Expected one wheel and one source archive')
            for artifact in (*wheels,*sources):
                run('archive:'+artifact.name,[sys.executable,'scripts/inspect_reference_wheel.py',str(artifact)])
            installed=directory/'installed'
            run('install',[sys.executable,'-m','pip','install','--no-deps','--disable-pip-version-check','--target',str(installed),str(wheels[0])])
            code='''
import sys
sys.path.insert(0,sys.argv[1])
from stratbox.capabilities.catalog import standard_catalog
from stratbox.capabilities.catalog.domains import load_domains
from stratbox.sdk import StrategyBox
from stratbox.shared.reference.assets import load_reference
assert standard_catalog().definitions
assert len(load_domains().domains)==5
for family in ('banks','geography','okved2'):
    load_reference('stratbox.shared.reference.'+family).validate_all()
with StrategyBox() as box:
    assert box.discover(kind='command',limit=1).entries
'''
            run('installed_metadata',[sys.executable,'-I','-S','-B','-c',code,str(installed)],directory)
            run('zip_metadata',[sys.executable,'-I','-S','-B','-c',code,str(wheels[0])],directory)
        report['result']='passed'
    except Exception as error:
        report['result']='failed';report['error']=str(error)
    finally:
        report['finished_at']=datetime.now(timezone.utc).isoformat()
        report_path.parent.mkdir(parents=True,exist_ok=True)
        report_path.write_text(json.dumps(report,indent=2)+'\n')
    return report


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,default=ROOT/'_mw/epochs-001-strategy-box-development/refactoring/standard-commands/release-check.json')
    parser.add_argument('--skip-pytest',action='store_true')
    args=parser.parse_args()
    result=check(args.report,full_pytest=not args.skip_pytest)
    print('Local release:',result['result'])
    return result['result']!='passed'


if __name__=='__main__':
    raise SystemExit(main())
