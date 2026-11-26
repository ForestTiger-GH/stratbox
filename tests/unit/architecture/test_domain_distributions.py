"""Every actual model and domain catalog is required in a delivered package."""
from pathlib import Path
import pytest
from .test_implementation_distributions import tool, write_archive, ROOT


@pytest.mark.parametrize('family',('cbr','fns','minfin','frank_rg','rosstat'))
def test_omitted_domain_root_is_rejected(tmp_path,family):
    check=tool();source=ROOT/'src/stratbox';inventory=check['inventory']()
    archive=tmp_path/'stratbox-test.whl'
    write_archive(archive,source,inventory,missing=(f'domains/{family}/domain.py',))
    with pytest.raises(ValueError,match='archive.mismatch'):check['inspect_archive'](archive)


def test_every_crosswalk_csv_and_every_financial_model_are_individually_required(tmp_path):
    check=tool();source=ROOT/'src/stratbox';inventory=check['inventory']()
    assets=[name for name in inventory if '/sors/crosswalk/_resources/' in name and name.endswith('.csv')
            or '/reporting_forms/models/' in name and name.endswith('.csv')]
    assert len(assets)>=9
    archive=tmp_path/'stratbox-test.whl'
    for name in assets:
        write_archive(archive,source,inventory,missing=(name,))
        with pytest.raises(ValueError,match='archive.mismatch'):check['inspect_archive'](archive)
    write_archive(archive,source,inventory,changed=(assets[0],))
    with pytest.raises(ValueError,match='archive.mismatch'):check['inspect_archive'](archive)
