# Локальная разработка stratbox

## Базовая установка

```bash
python -m pip install -e .
```

## Установка с тестами

```bash
python -m pip install -e ".[test]"
```

## Установка с PDF-поддержкой

```bash
python -m pip install -e ".[pdf]"
```

## Основные проверки

```bash
python scripts/check_release_integrity.py
python scripts/check_internal_imports.py
pytest -q
```

## Работа рядом с stratbox-windows

`stratbox-windows` должен ставить `stratbox` как внешнюю зависимость:

```bash
python -m pip install -e ../stratbox
python -m pip install -e ../stratbox-windows
```

Core-репозиторий нельзя снова превращать в смешанный монолит с surface-кодом.
