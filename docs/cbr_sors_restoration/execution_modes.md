# Режимы выполнения

## Strict certification

- `closure` — closure + feasibility, без target min/max;
- `targets` — явный region/class/metric scope;
- `priority` — наиболее узкие и перспективные unresolved-клетки;
- `all` — исчерпывающая сертификация.

`batch_size`, per-solve timeout, batch timeout, reset interval и retry задаются отдельно. После каждого batch модель получает новые bounds, запускает closure и компилируется заново. Неуспешная цель получает собственный статус и не уничтожает остальные результаты.

## Bridge

- `disabled` — стандарт;
- `optimum_only` — minimum reclassification benchmark;
- `targets` — benchmark + conditional min/max под objective cap.
