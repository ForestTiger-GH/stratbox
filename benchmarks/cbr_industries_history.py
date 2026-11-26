"""Benchmark actual offline industry source interpretation through the public SDK.

Usage: python benchmarks/cbr_industries_history.py --debt-dir /data/debt --output results.json
"""
from argparse import ArgumentParser
from datetime import datetime
from hashlib import sha256
import json
from pathlib import Path
import platform
import re
from statistics import median
from time import perf_counter

from stratbox import __version__
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material

SOURCES = {'debt': ('cbr.corporate_lending.debt_0105a', '01_05_A_Debt_corp_*.xlsx'),
           'issuance': ('cbr.corporate_lending.issuance_0104a', '01_04_A_New_loans_corp_*.xlsx')}


def run(series, paths):
    timings=[]; materials=[]; counts=[]
    with StrategyBox() as box:
        for path in paths:
            data=path.read_bytes()
            token=re.search(r'(20\d{6})',path.name)
            if token is None: raise ValueError('Filename requires an explicit issue date: '+path.name)
            issue=datetime.strptime(token.group(1),'%Y%m%d').date().isoformat()
            start=perf_counter()
            result=box.invoke('scenario.series.refresh',target=series,
                inputs={'material':Material(data,'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',series,
                    metadata={'filename':path.name,'issue_id':issue}),'issue':issue})
            timings.append(perf_counter()-start)
            if result.outcome!='succeeded': raise RuntimeError((path.name,result.outcome,result.diagnostics))
            value=result.output('dataset')
            counts.append(len(value.rows))
            materials.append({'file':path.name,'sha256':sha256(data).hexdigest(),'bytes':len(data),'dataset_identity':value.identity})
            result.close()
    return {'source':series,'files':len(paths),'rows':sum(counts),'seconds':sum(timings),
            'median_file_seconds':median(timings),'materials':materials}


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('--debt-dir',type=Path)
    parser.add_argument('--issuance-dir',type=Path)
    parser.add_argument('--max-files',type=int)
    parser.add_argument('--output',type=Path,default=Path('industries-benchmark.json'))
    args=parser.parse_args()
    if not(args.debt_dir or args.issuance_dir): parser.error('Supply an explicit source directory')
    reports=[]
    for kind,(series,pattern) in SOURCES.items():
        directory=getattr(args,kind+'_dir')
        if directory is not None:
            paths=sorted(directory.glob(pattern))
            if args.max_files is not None:
                if args.max_files<1: parser.error('--max-files must be positive')
                paths=paths[:args.max_files]
            if not paths: parser.error('No matching originals in '+str(directory))
            reports.append(run(series,paths))
    args.output.write_text(json.dumps({'stratbox':__version__,'python':platform.python_version(),'results':reports},indent=2)+'\n')


if __name__=='__main__':
    main()
