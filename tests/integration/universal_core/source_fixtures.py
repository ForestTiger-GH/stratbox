from datetime import date
import io
import json
import zipfile


def sample_xlsx(formula=False, extra_sheet=False, two_level=True):
    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    workbook = f'<workbook xmlns="{ns}" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"><sheets><sheet name="Региональный разрез" sheetId="1" r:id="rId1"/></sheets></workbook>'
    relations = '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships"><Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/></Relationships>'

    def string(col, rid, val):
        return f'<c r="{col}{rid}" t="inlineStr"><is><t>{val}</t></is></c>'

    def num(col, rid, val):
        return f'<c r="{col}{rid}"><v>{val}</v></c>'

    rows = [
        f'<row r="1">{string("A", 1, "Статистика территориального присутствия")}</row>'
    ]
    rows.append(
        f'<row r="2">{string("A", 2, "Территория")}{string("B", 2, "Кредитные организации")}{string("C", 2, "Филиалы")}{string("D", 2, "Мобильные офисы")}{string("E", 2, "Всего")}</row>'
    )
    regions = ["Российская Федерация"] + [
        "Белгородская область",
        "Брянская область",
        "Республика Алтай",
    ] * 15
    for i, reg in enumerate(regions, 3):
        form = "<f>2+3</f>" if formula and i == 3 else ""
        rows.append(
            f'<row r="{i}">{string("A", i, reg)}{num("B", i, 2)}{num("C", i, 3)}<c r="D{i}">{form}<v>5</v></c>{num("E", i, 10)}</row>'
        )
    sheet = (
        f'<worksheet xmlns="{ns}"><sheetData>{"".join(rows)}</sheetData></worksheet>'
    )
    buff = io.BytesIO()
    with zipfile.ZipFile(buff, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("xl/workbook.xml", workbook)
        z.writestr("xl/_rels/workbook.xml.rels", relations)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    return buff.getvalue()


def sample_page():
    links = "".join(
        f'<a href="/vfs/statistics/bank_system/DivisionsPerRegion_01{mo:02d}20.xlsx">2020 г.: на 01.{mo:02d}</a>'
        for mo in range(1, 13)
    )
    links += '<a href="/vfs/statistics/bank_system/DivisionsPerRegion_010719.xlsx">2019 г.: на 01.07</a>'
    links += '<a href="/vfs/statistics/bank_system/DivisionsPerRegion_011026.xlsx">2026 г.: на 01.10</a>'
    return "<html><body>" + links + "</body></html>"


def fixture(d=date(2026, 11, 10), count=89, *, as_strings=False):
    day = d.strftime("%d.%m.%Y") + " 00:00:00"
    regional = []
    for i in range(1, count + 1):
        vals = {
            "stat_date": day,
            "cnt_level": 0,
            "ssrf": str(i).zfill(2),
            "name": f"Region {i:02d}",
            "cnt_name": f"Region {i:02d}",
            "cnt_total": 101,
            "cnt_ul_total": 51,
            "cnt_ip_total": 50,
            "cnt_ul_micro": 40,
            "cnt_ul_mini": 10,
            "cnt_ul_normal": 1,
            "cnt_ip_micro": 45,
            "cnt_ip_mini": 4,
            "cnt_ip_normal": 1,
        }
        if as_strings:
            for k in list(vals):
                if k.startswith("cnt_") and k != "cnt_name" and k != "cnt_level":
                    vals[k] = str(vals[k])
        regional.append(vals)
    national = {
        "stat_date": day,
        "cnt_level": 2,
        "cnt_name": "Российская Федерация",
        "cnt_total": 101 * count,
        "cnt_ul_total": 51 * count,
        "cnt_ip_total": 50 * count,
    }
    districts = [
        {"stat_date": day, "cnt_level": 1, "cnt_name": f"District {i}"}
        for i in range(9)
    ]
    return [national] + districts + regional


def encoded(items):
    return json.dumps(items, ensure_ascii=False).encode("utf-8")


FORM_EPOCHS = (
    (
        date(2012, 1, 1),
        "A",
        (1, 11),
        "1010 1020 1021 1022 1023 1024 1025 1026 1030 1031 1032 1033",
    ),
    (
        date(2016, 1, 1),
        "B",
        (1, 11),
        "1010 1020 1021 1022 1023 1024 1025 1026 1027 1028 1029 1040",
    ),
    (
        date(2020, 1, 1),
        "C1",
        (1, 12),
        "1000 1100 1110 1120 1130 1131 1140 1141 1142 1143 1144 1200",
    ),
    (
        date(2022, 1, 1),
        "C2",
        (1, 9, 13),
        "1000 1100 1110 1120 1130 1131 1140 1141 1142 1143 1144 1200",
    ),
    (
        date(2026, 11, 1),
        "C3",
        (1, 8, 12),
        "1000 1100 1110 1120 1130 1131 1140 1141 1142 1143 1144 1200",
    ),
)


def form_workbook(indicators, kinds, *, legacy=False):
    """Construct the publisher's two workbook orientations using synthetic counts."""
    kinds = kinds.split()
    if legacy:
        import xlwt

        workbook = xlwt.Workbook()

        def sheet(name):
            output = workbook.add_sheet(name)
            return lambda row, col, value: output.write(row, col, value)
    else:
        from openpyxl import Workbook

        workbook = Workbook()
        workbook.remove(workbook.active)

        def sheet(name):
            output = workbook.create_sheet(name)
            return lambda row, col, value: output.cell(row + 1, col + 1, value)

    national = "Российская Федерация"
    districts = [f"Округ {n} федеральный округ" for n in range(6)]
    subjects = [(str(n).zfill(2), f"Субъект {n}") for n in range(1, 61)]
    geography = [("", national)] + [("", name) for name in districts] + subjects
    controls = {
        national: sheet(national),
        **{code: sheet(code) for code, _ in subjects},
    }
    for position, kind in enumerate(kinds):
        target = sheet(kind)
        target(5, 2, "Количество юридических лиц")
        if len(indicators) == 3:
            target(5, 3, "В отношении которых введены процедуры банкротства")
        target(5, len(indicators) + 1, "Ликвидация в порядке банкротства")
        target(9, 0, "А")
        target(9, 1, "Б")
        for index, number in enumerate(indicators, 2):
            target(9, index, number)
        for index, (code, label) in enumerate(geography, 10):
            if code:
                target(index, 0, code)
            target(index, 1, label)
            if code or label == national:
                control = controls[code or label]
                control(position, 0, f"Вид {kind}")
                control(position, 1, kind)
            for col, _ in enumerate(indicators, 2):
                value = 60 if label == national else 1
                target(index, col, value)
                if code or label == national:
                    control(position, col, value)
    out = io.BytesIO()
    workbook.save(out)
    return out.getvalue()
