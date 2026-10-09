# Target HOW — набор опровержимых проверок

**Контракт:** кандидатное `TH-SB-2026-10-09-CANDIDATE-1`; ни одна строка не утверждает, что test уже существует или проходит. Цель — проверить будущую **допущенную** реализацию, отделяя требование, тестовый механизм и наблюдаемое доказательство.

| Vector | WHAT concern | Fault/condition | Expected user-visible/proof outcome | Admission dependency |
| --- | --- | --- | --- | --- |
| V01 | TW-C01 | Source missing vs timeout | Два различных результата; ни один не подставляет zero без provenance | Product source/error policy |
| V02 | TW-C02 | Worker completed, analytical validation failed | Отдельные execution terminal и domain qualification | Defined state semantics |
| V03 | TW-C03 | Cancel после возможного внешнего effect | Невозможен ложный `cancelled without effect`; проверка receipt | Cancellation/effect policy |
| V04 | TW-C04 | Дублирующая команда с тем же key/digest | Нет второго логического effect в принятом scope | Idempotency window |
| V05 | TW-C04 | Тот же key с другим digest | Контролируемый conflict | API design and authority |
| V06 | TW-C06 | Disk full между staged write и publish | Нет видимого committed artifact; staged recovery | Artifact identity/write contract |
| V07 | TW-C02 | Crash между durable completion и UI refresh | Reconnect показывает подтверждённый результат из authority | Persistence profile |
| V08 | TW-C05 | Другой пользователь читает чужой Run/log | Denied и отсутствие утечки metadata | Shared-node authorization |
| V09 | Boundary accepted | Импорт core без UI toolkit | Headless import/operation сохраняет работоспособность | Versioned core packages |
| V10 | Boundary accepted | Изменяется внешняя platform version | Compatibility/unsupported status, нет выдуманной удалённой функции | Exact external contract |
| V11 | TW-C07 | Смена Windows renderer на иной поддержанный frontend | Operation/Scenario семантика одинакова при различном представлении | Product surface profile |
| V12 | TW-C02/06 | Повреждение JSON как единственного долговременного state | Явный degraded/failure; новые операции не уничтожают доказательства | Data durability policy |
| V13 | TW-C04 | Worker lease expires, старый worker завершает поздно | Fenced старый commit отклонён | Chosen resource/authority protocol |
| V14 | TW-C01 | Округлённые банковские суммы не складываются по целым | Evidence сохраняет latent/publication distinction | Domain result contract |

**Тестовая запись** после фактического исполнения должна содержать exact product, code, schema, data/fixtures, external contract, environment, step, timestamp, observed outputs, decision and gate status. Таблица — план верификации, **не** report о выполненном тестировании.
