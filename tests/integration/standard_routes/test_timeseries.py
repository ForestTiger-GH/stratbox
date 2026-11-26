"""A database selection and whole-table application share the same series contract."""
from decimal import Decimal
from stratbox.sdk import StrategyBox
from stratbox.shared.data.values import SourceDataset, TimeSeries, SnapshotRef, TimeSeriesAdjustment, AdjustmentDiagnostics, fingerprint


class Backend:
    def __init__(self): self.called=[]
    def adjust(self,series,*,settings,checkpoint):
        checkpoint()
        self.called.append(series.coordinates['metric'])
        return TimeSeriesAdjustment(fingerprint(series),series,series,'synthetic_test_backend',
            AdjustmentDiagnostics(fingerprint(series),{'residual_seasonality':True,'outlier_policy':True}))


class Reader:
    def __init__(self,dataset): self.dataset=dataset;self.calls=[]
    def query(self,reference,query):
        self.calls.append((reference,query))
        rows=tuple(row for row in self.dataset.rows if all(row.get(key)==value for key,value in query.items()))
        return SourceDataset(self.dataset.source_id,rows,self.dataset.semantics)


def data():
    return SourceDataset('fixture.history',tuple({'metric':metric,'subject':'RU','unit':'count',
        'frequency':'monthly','measure_kind':'flow','period':f'2026-{month:02d}',
        'value':Decimal(month),'value_status':'reported'}
        for metric in ('credit','deposits') for month in range(1,7)))


def test_database_filter_one_series_and_same_command_over_whole_table():
    dataset=data();reader=Reader(dataset);backend=Backend()
    with StrategyBox(providers={'dataset_reader':reader,'seasonal_adjustment':backend}) as box:
        selected=box.invoke('command.dataset.query',inputs={
            'reference':SnapshotRef('history','fixture','content'), 'query':{'metric':'credit'}})
        assert selected.outcome=='succeeded',selected.diagnostics
        prepared=box.invoke('command.timeseries.prepare',inputs={'observations':selected.output('observations')})
        assert prepared.outcome=='succeeded',prepared.diagnostics
        single=box.invoke('operation.timeseries.adjust',inputs={'series':prepared.output('series')})
        assert single.outcome=='succeeded',single.diagnostics
        assert len(single.output('adjustment').adjusted.values)==6
        batch=box.invoke('operation.calculation.apply_table',inputs={'table':dataset})
        assert batch.outcome=='succeeded',batch.diagnostics
        assert len(batch.output('results'))==2
        assert tuple((item.ordinal,item.outcome) for item in batch.output('outcomes'))==((0,'succeeded'),(1,'succeeded'))
        assert sorted(backend.called)==['credit','credit','deposits']
        credit=next(item for item in batch.output('results') if item.original.coordinates['metric']=='credit')
        assert single.output('adjustment').adjusted.values==credit.adjusted.values
        assert len(reader.calls)==1
