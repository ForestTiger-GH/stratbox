"""Discover standard callables and prepare independent source jobs in one service."""
from argparse import ArgumentParser
from pathlib import Path
from stratbox.capabilities.preparation import InvocationRequest
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path)
    parser.add_argument('--issue',required=True)
    args=parser.parse_args()
    with StrategyBox() as box:
        print([entry['id'] for entry in box.discover(kind='scenario').entries])
        request=InvocationRequest('scenario.series.refresh',
            {'material':Material(args.file.read_bytes(),'application/json','fns.sme'),'issue':args.issue},target='fns.sme')
        plan=box.prepare('cascade.sources.refresh',inputs={'members':(request,)})
        handle=box.submit(plan)
        result=handle.result(timeout=60)
        print(handle.snapshot())
        print(result.outcome,result.diagnostics)
        if result.outcome=='succeeded':
            print([len(value.rows) for value in result.output('results')])
        result.close()
    return result.outcome!='succeeded'


if __name__=='__main__':
    raise SystemExit(main())
