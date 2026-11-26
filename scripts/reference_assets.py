"""Verify the directly declared packaged reference contents by exact bytes."""
from pathlib import Path
import argparse
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'src'))
from stratbox.shared.reference.assets import load_reference


def verify(reference='all'):
    families=('banks','geography','okved2') if reference=='all' else (reference,)
    for family in families:
        value=load_reference('stratbox.shared.reference.'+family)
        value.validate_all()
        print('OK',family,value.snapshot_identity.sha256)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference',choices=('all','banks','geography','okved2'),default='all')
    verify(parser.parse_args().reference)
