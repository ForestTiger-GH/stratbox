"""Retain exact bytes and read the verified immutable reference."""
from argparse import ArgumentParser
from pathlib import Path
from stratbox.core.storage.filestore import LocalFileStore
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import Material


def main():
    parser=ArgumentParser(description=__doc__)
    parser.add_argument('file',type=Path)
    parser.add_argument('--root',type=Path,required=True)
    args=parser.parse_args()
    original=Material(args.file.read_bytes())
    with StrategyBox(providers={'filestore':LocalFileStore(str(args.root))}) as box:
        saved=box.invoke('command.artifact.commit',inputs={'material':original,'destination':'objects'})
        assert saved.outcome=='succeeded',saved.diagnostics
        restored=box.invoke('command.material.read',inputs={'location':saved.output('reference')})
        assert restored.output('material').data==original.data
        print(saved.output('reference'))
        saved.close();restored.close()


if __name__=='__main__':
    main()
