"""
excel_xlsx — чтение/запись XLSX поверх FileStore.

Зависимости:
- pandas
- openpyxl (опционально; можно включить автоподкачку через STRATBOX_AUTO_PIP=1)
"""

from __future__ import annotations

from io import BytesIO
from typing import Any

import pandas as pd

from stratbox.base.filestore.base import FileStore
from stratbox.base.ioapi.bytes import read_bytes, write_bytes
from stratbox.base.utils.optional_deps import ensure_import


def _fit_column_widths(
    ws,
    *,
    min_width: float | None,
    max_width: float | None,
    sample_rows: int = 2000,
    max_cell_chars: int = 60,
    include_header: bool = False,
    header_max_chars: int = 22,
    padding: float = 2.8,
    filter_padding: float = 2.0,
) -> None:
    """
    Авто-настройка ширины столбцов по содержимому.

    Критично для CBR-таблиц:
    - По умолчанию заголовок (строка 1) НЕ участвует в оценке ширины,
      иначе длинные подписи столбцов раздувают ширину "в космос".
    - Каждый столбец рассчитывается индивидуально.
    - Ошибка в одной "кривой" колонке не должна ломать автофит остальных.
    """
    import datetime as _dt
    from openpyxl.utils import get_column_letter

    max_row = ws.max_row or 1
    max_col = ws.max_column or 1
    last_row = min(max_row, int(sample_rows)) if sample_rows and sample_rows > 0 else max_row

    # Где начинать мерить данные:
    # если заголовок не учитывается, начинаем со 2-й строки
    start_row = 1 if include_header else 2
    if start_row > last_row:
        start_row = 1  # если лист крошечный

    # Флаг: есть ли автофильтр на листе (если да — добавляем место под стрелку)
    has_filter = False
    try:
        has_filter = bool(ws.auto_filter and getattr(ws.auto_filter, "ref", None))
    except Exception:
        has_filter = False

    for c in range(1, max_col + 1):
        try:
            col_max = 0

            # 1) Опционально учитываем заголовок (строка 1), но сильно ограничиваем его вклад
            if include_header and max_row >= 1:
                cell = ws.cell(row=1, column=c)
                if cell.coordinate not in ws.merged_cells:
                    v = cell.value
                    if v is not None:
                        s = str(v).replace("\n", " ").strip()
                        if s:
                            if header_max_chars and len(s) > int(header_max_chars):
                                s = s[: int(header_max_chars)]
                            col_max = max(col_max, len(s))

            # 2) Основная оценка — по значениям
            for r in range(start_row, last_row + 1):
                cell = ws.cell(row=r, column=c)

                # merged cells: значение только в верхней-левой; остальные пропускаем
                if cell.coordinate in ws.merged_cells:
                    continue

                v = cell.value
                if v is None:
                    continue

                # Формулы не учитываются (их текст длинный, а отображаемое значение короткое)
                if isinstance(v, str) and v.startswith("="):
                    continue

                # Приведение к "отображаемой" строке
                if isinstance(v, (_dt.date, _dt.datetime)):
                    s = (
                        v.strftime("%Y-%m-%d")
                        if isinstance(v, _dt.date) and not isinstance(v, _dt.datetime)
                        else v.strftime("%Y-%m-%d %H:%M")
                    )
                elif isinstance(v, (int, float)):
                    # ограничиваем float-«простыни»
                    s = f"{v:.15g}"
                else:
                    s = str(v)

                s = s.replace("\n", " ").strip()
                if not s:
                    continue

                # НЕ даём одной ячейке раздувать колонку бесконечно
                if max_cell_chars and len(s) > int(max_cell_chars):
                    s = s[: int(max_cell_chars)]

                col_max = max(col_max, len(s))

            # Если колонка пустая — можно оставить min_width
            if col_max <= 0:
                if min_width is not None:
                    col_letter = get_column_letter(c)
                    ws.column_dimensions[col_letter].width = float(min_width)
                continue

            # Перевод символов в "excel width" + небольшой запас.
            # Коэффициент >1.0 нужен, потому что ширина символов неодинакова,
            # плюс Excel добавляет внутренние отступы.
            width = float(col_max * 1.08 + float(padding))

            # Если на листе включён автофильтр — Excel добавляет место под стрелку фильтра
            if has_filter:
                width += float(filter_padding)

            if min_width is not None:
                width = max(width, float(min_width))
            if max_width is not None:
                width = min(width, float(max_width))

            col_letter = get_column_letter(c)
            ws.column_dimensions[col_letter].width = width

        except Exception as e:
            # Не валить весь лист из-за одной проблемной колонки
            print(f"[WARN] Auto width skipped column {c}: {e}")
            continue


def read_df(
    path: str,
    store: FileStore | None = None,
    *,
    auto_install: bool | None = None,
    **kwargs: Any,
) -> pd.DataFrame:
    # openpyxl нужен pandas'у как engine для xlsx
    ensure_import("openpyxl", "openpyxl>=3.1", auto_install=auto_install)

    data = read_bytes(path, store=store)
    return pd.read_excel(BytesIO(data), engine="openpyxl", **kwargs)


def write_df(
    path: str,
    df: pd.DataFrame,
    store: FileStore | None = None,
    *,
    sheet_name: str = "data",
    meta: dict[str, Any] | None = None,
    style_preset: str | None = "DEFAULT",
    freeze_panes: str | None = None,
    auto_col_width: bool = True,
    col_width_min: float | None = 6.0,
    col_width_max: float | None = 60.0,
    col_width_sample_rows: int = 2000,
    col_width_include_header: bool = False,
    col_width_header_max_chars: int = 22,
    col_width_padding: float = 2.8,
    col_width_filter_padding: float = 2.0,
    auto_install: bool | None = None,
    index: bool = False,
    **kwargs: Any,
) -> None:
    """
    Пишет DataFrame в XLSX и (опционально) применяет:
    - sheet_name
    - метаданные книги (meta)
    - форматирование (style_preset)
    - автофильтр (через autofilter_range)
    - автоподбор ширины столбцов

    style_preset:
    - None => стили не применять
    - "DEFAULT" => применить дефолтный пресет (core или plugin)
    - либо конкретное имя пресета (core или plugin)

    Автофильтр:
    - можно передать autofilter_range="A1:Z200" через kwargs или engine_kwargs
    - если не передан, диапазон будет сгенерирован автоматически
    """
    ensure_import("openpyxl", "openpyxl>=3.1", auto_install=auto_install)

    from openpyxl import load_workbook
    from stratbox.base.styles.excel.main import apply_preset

    bio = BytesIO()

    # ВАЖНО: index контролируется явно, чтобы не получить конфликт kwargs
    if "index" in kwargs:
        kwargs.pop("index")

    # --- ВАЖНО: pandas/openpyxl в некоторых окружениях не принимает autofilter_range в writer._write_cells.
    # Поэтому этот параметр надо извлечь и применить вручную через openpyxl уже ПОСЛЕ записи.
    autofilter_range = None

    if "autofilter_range" in kwargs:
        autofilter_range = kwargs.pop("autofilter_range")

    engine_kwargs = kwargs.pop("engine_kwargs", None)
    if isinstance(engine_kwargs, dict) and "autofilter_range" in engine_kwargs:
        autofilter_range = engine_kwargs.pop("autofilter_range")
        # Если там остались другие engine_kwargs — безопаснее сейчас НЕ прокидывать их дальше,
        # чтобы не поймать несовместимость в разных версиях pandas/openpyxl.

    df.to_excel(bio, index=index, engine="openpyxl", sheet_name=sheet_name, **kwargs)

    # пост-обработка через openpyxl
    bio2 = BytesIO(bio.getvalue())
    wb = load_workbook(bio2)

    # 1) метаданные
    if meta:
        props = wb.properties
        if "creator" in meta:
            props.creator = str(meta["creator"])
        if "title" in meta:
            props.title = str(meta["title"])
        if "subject" in meta:
            props.subject = str(meta["subject"])
        if "category" in meta:
            props.category = str(meta["category"])
        if "keywords" in meta:
            props.keywords = str(meta["keywords"])
        if "description" in meta:
            props.description = str(meta["description"])

    ws = wb[sheet_name] if sheet_name in wb.sheetnames else wb.active

    # 2) стили (если заданы)
    if style_preset is not None:
        apply_preset(ws, style_preset, freeze_panes=freeze_panes)

    # 3) автофильтр — СНАЧАЛА, чтобы автоширина могла учитывать плашку фильтра
    if autofilter_range:
        try:
            ws.auto_filter.ref = str(autofilter_range)
        except Exception:
            pass

    if not autofilter_range:
        try:
            from openpyxl.utils import get_column_letter

            # диапазон таблицы: учитывается index, если index=True
            ncols = int(df.shape[1]) + (1 if index else 0)
            nrows = int(df.shape[0]) + 1  # +1 строка заголовка
            if ncols > 0 and nrows > 1:
                autofilter_range = f"A1:{get_column_letter(ncols)}{nrows}"
                ws.auto_filter.ref = autofilter_range
        except Exception:
            pass

    # 4) авто-настройка ширины столбцов (после автофильтра!)
    if auto_col_width:
        try:
            _fit_column_widths(
                ws,
                min_width=col_width_min,
                max_width=col_width_max,
                sample_rows=col_width_sample_rows,
                include_header=col_width_include_header,
                header_max_chars=col_width_header_max_chars,
                padding=col_width_padding,
                filter_padding=col_width_filter_padding,
            )
        except Exception as e:
            print(f"[WARN] Auto column width failed: {e}")

    out = BytesIO()
    wb.save(out)

    write_bytes(path, out.getvalue(), store=store)
