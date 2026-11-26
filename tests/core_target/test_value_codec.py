"""Portable scientific content through the current standard value commands."""
from dataclasses import replace
from datetime import date, datetime, timezone
from decimal import Decimal
import json
import struct
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd
import pytest

from stratbox.sdk import StrategyBox
from stratbox.core.execution.service import ExecutionSettings
from stratbox.core.limits import ExecutionBudget
from stratbox.shared.data.values import SourceDataset, EncodedProduct, Material, Assessment, fingerprint
from stratbox.shared.data.coverage import SnapshotCoverage, CoverageDimension
from stratbox.shared.data.assessment import CoverageAssessment, CoverageCoordinate, ProcessingFinding
from stratbox.shared.data.source_context import SourceUse, SourceCoordinate
from stratbox.shared.data.workbook_cells import WorkbookCell, SheetCells, WorkbookCells
from stratbox.shared.identity import ByteIdentity
from stratbox.shared.evidence import UsedInputReceipt


def encoded(box,value):
    result=box.invoke('command.value.encode',inputs={'value':value})
    assert result.outcome=='succeeded',result.diagnostics
    return result.output('representation')


def roundtrip(value):
    with StrategyBox() as box:
        representation=encoded(box,value)
        result=box.invoke('command.value.decode',inputs={'representation':representation})
        assert result.outcome=='succeeded',result.diagnostics
        return result.output('value')


def test_portable_dataset_preserves_units_periods_actual_sources_and_partial_coverage():
    source=ByteIdentity.of(b'original workbook')
    lineage=(UsedInputReceipt('original',source,'text/csv','reference_only','publisher.series'),)
    use=SourceUse(SourceCoordinate('publisher.series',issue_id='2026-09',asset_id='main',material_identity=source),
                  'input','domain_validated','sha256:'+source.sha256)
    coverage=SnapshotCoverage('partial','One selected region',(
        CoverageDimension('region',requested=('A','B'),output=('A',),missing=('B',)),))
    value=SourceDataset('publisher.series',({'period':date(2026,9,1),'value':Decimal('17.250'),'unit':'RUB',
        'scale':Decimal(1000000),'value_status':'reported'},),{'measure_kind':'stock'},'2026-09',lineage,
        Assessment('partial',('one_region_missing',),qualifications=frozenset({'reported','partial'}),coverage=coverage),source_uses=(use,))
    restored=roundtrip(value)
    assert restored==value and restored.identity==value.identity
    assert not restored.assessment.complete and restored.assessment.coverage.dimensions[0].missing==('B',)
    assert restored.rows[0]['value'].as_tuple()==Decimal('17.250').as_tuple()
    assert restored.source_uses==(use,) and restored.lineage==lineage


def test_scalar_collection_preserves_order_literals_binary_and_ieee_payloads():
    nan=struct.unpack('>d',bytes.fromhex('7ff8000000000042'))[0]
    value=(Decimal('1e999999'),b'binary',-0.0,nan,float('inf'),(1,True),'str')
    restored=roundtrip(value)
    assert type(restored) is tuple and str(restored[0])=='1E+999999'
    assert restored[:2]==value[:2] and restored[-2:]==value[-2:]
    for before,after in zip(value[2:5],restored[2:5],strict=True):
        assert struct.pack('>d',before)==struct.pack('>d',after)
    assert fingerprint((1,2))!=fingerprint((2,1))
    assert fingerprint((1,))!=fingerprint((1,1))


def test_dataframe_preserves_axes_categories_nulls_tuple_cells_and_nan_payload():
    nan=struct.unpack('>d',bytes.fromhex('7ff8000000000042'))[0]
    frame=pd.DataFrame({'count':pd.array([1,None],dtype='Int64'),
        'kind':pd.Categorical(['a','b'],categories=['unused','b','a'],ordered=True),
        'raw':pd.Series([None,nan],dtype=object),'key':pd.Series([('A',1),('B',2)],dtype=object)})
    frame.index=pd.MultiIndex.from_tuples([('A',1),('B',2)],names=['region','rank'])
    restored=roundtrip(frame)
    pd.testing.assert_frame_equal(restored,frame)
    assert restored.iloc[0,2] is None
    assert struct.pack('>d',restored.iloc[1,2])==bytes.fromhex('7ff8000000000042')
    assert tuple(restored['kind'].cat.categories)==('unused','b','a')
    assert fingerprint(frame)!=fingerprint(frame.iloc[::-1])
    assert fingerprint(frame)!=fingerprint(frame.astype({'count':'Float64'}))


def test_full_workbook_evidence_retains_formula_cache_lexeme_style_and_original_bytes_identity():
    cells=(WorkbookCell(1,1,'A1',Decimal('1.20'),'1.20','n','SUM(B1:C1)','0.00',1,(('t','shared'),)),
           WorkbookCell(1,2,'B1','reported','reported','str'))
    source=ByteIdentity.of(b'original workbook')
    value=WorkbookCells((SheetCells('budget',0,1,2,cells,('A1:B1',)),),source)
    restored=roundtrip(value)
    assert restored==value and restored.identity==source
    assert restored.sheets[0].cells[0].formula=='SUM(B1:C1)'
    assert restored.sheets[0].cells[0].value==Decimal('1.20')
    assert fingerprint(restored)!=source.sha256


def test_actual_coverage_coordinates_and_findings_have_data_only_portable_types():
    actual=CoverageCoordinate('regions','A','debt','as_of','2026-09-01','resident',(('currency','RUB'),))
    missing=replace(actual,subject_id='B')
    coverage=CoverageAssessment('selected.sheet',(actual.identity,),True,('region:A',),
        source_identity=ByteIdentity.of(b'original'),expected_coordinates=(actual,missing))
    finding=ProcessingFinding('source.missing','warning',1,'One declared observation is absent.')
    assert roundtrip((actual,coverage,finding))==(actual,coverage,finding)
    assert coverage.status=='partial'


def test_intrinsic_semantics_and_typed_source_uses_contribute_to_value_identity():
    value=SourceDataset('publisher.series',({'value':Decimal('1.00')},),{'unit':'RUB'})
    assert value.identity!=replace(value,semantics={'unit':'USD'}).identity
    assert value.identity!=replace(value,rows=({'value':Decimal('2.00')},)).identity
    material=ByteIdentity.of(b'original')
    left=SourceUse(SourceCoordinate('publisher.series',issue_id='left',material_identity=material),'input','domain_validated')
    right=replace(left,coordinate=replace(left.coordinate,issue_id='right'))
    assert replace(value,source_uses=(left,)).identity!=replace(value,source_uses=(right,)).identity


def test_raw_original_and_encoded_product_preserve_charset_lineage_and_media_type():
    source=Material(b'original','text/csv','publisher.issue',charset='utf-8')
    product=EncodedProduct(b'region,value\nA,1\n','text/csv',lineage=(source.identity,),descriptor={'encoding':'utf-8'})
    assert roundtrip(source)==source
    assert roundtrip(product)==product


def test_descriptor_identity_rejects_changed_encoded_content():
    with StrategyBox() as box:
        value=encoded(box,7)
        changed=replace(value,data=b'8')
        response=box.invoke('command.value.decode',inputs={'representation':changed})
        assert response.outcome=='failed' and 'value' not in response.outputs
        assert any('identity_mismatch' in code for code in response.diagnostics)


def test_encoding_byte_limit_rejects_output_without_a_partial_representation():
    with StrategyBox() as box:
        result=box.invoke('command.value.encode',inputs={'value':b'x'*1000},parameters={'max_bytes':100})
    assert result.outcome=='failed' and 'representation' not in result.outputs


@pytest.mark.parametrize('command', ['encode','decode'])
def test_collection_of_frames_obeys_one_aggregate_cell_ceiling(command):
    frame=pd.DataFrame({'a':[1,2],'b':[3,4]})
    with StrategyBox() as box:
        representation=encoded(box,(frame,frame))
    settings=ExecutionSettings(run_limits=ExecutionBudget(cells=7))
    with StrategyBox(settings=settings) as box:
        inputs={'value':(frame,frame)} if command=='encode' else {'representation':representation}
        result=box.invoke('command.value.'+command,inputs=inputs)
    assert result.outcome=='failed' and not result.outputs
    assert any('cells' in code for code in result.diagnostics)


def test_pandas_scalar_nanoseconds_and_named_timestamp_zone_are_preserved():
    values=(pd.NA,pd.NaT,pd.Timestamp('2026-11-23T12:00:00.000000001',tz='Europe/Helsinki'),pd.Timedelta(1,unit='ns'))
    restored=roundtrip(values)
    assert restored[0] is pd.NA and restored[1] is pd.NaT
    assert restored[2].value==values[2].value and str(restored[2].tz)==str(values[2].tz)
    assert restored[3].value==1


def test_named_python_timezone_keeps_dst_identity_in_portable_datetime():
    value=datetime(2026,7,1,12,0,tzinfo=ZoneInfo('Europe/Helsinki'))
    restored=roundtrip(value)
    assert restored==value
    assert getattr(restored.tzinfo,'key',None)=='Europe/Helsinki'
