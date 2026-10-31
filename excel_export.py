"""Export a league snapshot to a standalone Excel workbook using Python's stdlib."""

import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
REL_NS = "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
PKG_REL_NS = "http://schemas.openxmlformats.org/package/2006/relationships"
CONTENT_NS = "http://schemas.openxmlformats.org/package/2006/content-types"

ET.register_namespace("", MAIN_NS)
ET.register_namespace("r", REL_NS)


def _tag(name):
    return "{{{}}}{}".format(MAIN_NS, name)


def _add_cell(row, column, row_number, value=None, style=0, formula=None):
    attributes = {"r": "{}{}".format(column, row_number), "s": str(style)}
    if formula is not None:
        cell = ET.SubElement(row, _tag("c"), attributes)
        ET.SubElement(cell, _tag("f")).text = (
            formula[1:] if formula.startswith("=") else formula
        )
    elif value is not None:
        cell = ET.SubElement(row, _tag("c"), attributes)
        if isinstance(value, (int, float)):
            ET.SubElement(cell, _tag("v")).text = str(value)
        else:
            cell.set("t", "inlineStr")
            inline = ET.SubElement(cell, _tag("is"))
            ET.SubElement(inline, _tag("t")).text = str(value)
    elif style:
        ET.SubElement(row, _tag("c"), attributes)


def _add_row(sheet_data, row_number, cells):
    row = ET.SubElement(sheet_data, _tag("row"), {"r": str(row_number)})
    for column, value, style, formula in cells:
        _add_cell(row, column, row_number, value, style, formula)
    return row


def _add_sheet_views(root, freeze_row):
    views = ET.Element(_tag("sheetViews"))
    view = ET.SubElement(views, _tag("sheetView"), {"workbookViewId": "0"})
    ET.SubElement(
        view,
        _tag("pane"),
        {
            "ySplit": str(freeze_row),
            "topLeftCell": "A{}".format(freeze_row + 1),
            "activePane": "bottomLeft",
            "state": "frozen",
        },
    )
    ET.SubElement(view, _tag("selection"), {"pane": "bottomLeft"})
    root.insert(0, views)


def _add_columns(root, widths, hidden=()):
    columns = ET.Element(_tag("cols"))
    for index, width in enumerate(widths, start=1):
        attributes = {
            "min": str(index),
            "max": str(index),
            "width": str(width),
            "customWidth": "1",
        }
        if index in hidden:
            attributes["hidden"] = "1"
        ET.SubElement(
            columns,
            _tag("col"),
            attributes,
        )
    root.insert(1, columns)


def _add_validation(root, cell_range):
    validations = ET.SubElement(root, _tag("dataValidations"), {"count": "1"})
    validation = ET.SubElement(
        validations,
        _tag("dataValidation"),
        {
            "type": "whole",
            "operator": "between",
            "allowBlank": "1",
            "showErrorMessage": "1",
            "errorTitle": "Nieprawidłowy wynik",
            "error": "Wynik musi być nieujemną liczbą całkowitą.",
            "sqref": cell_range,
        },
    )
    ET.SubElement(validation, _tag("formula1")).text = "0"
    ET.SubElement(validation, _tag("formula2")).text = "999"


def _add_filter(root, cell_range):
    ET.SubElement(root, _tag("autoFilter"), {"ref": cell_range})


def _add_merge(root, ranges):
    merged = ET.SubElement(root, _tag("mergeCells"), {"count": str(len(ranges))})
    for cell_range in ranges:
        ET.SubElement(merged, _tag("mergeCell"), {"ref": cell_range})


def _sheet_standings(teams, fixture_last_row):
    root = ET.Element(_tag("worksheet"))
    _add_sheet_views(root, 4)
    _add_columns(root, [10, 30, 12, 12, 20, 20, 12])
    data = ET.SubElement(root, _tag("sheetData"))
    _add_row(data, 1, [("A", "Tabela ligowa", 1, None)])
    _add_row(
        data,
        2,
        [
            (
                "A",
                "Tabela aktualizuje się po zmianie wyników w arkuszu Mecze. "
                "Kolejność: punkty, bilans bramek, bramki strzelone, nazwa drużyny.",
                2,
                None,
            )
        ],
    )
    headers = (
        ("A", "Miejsce"),
        ("B", "Drużyna"),
        ("C", "Mecze"),
        ("D", "Punkty"),
        ("E", "Bramki strzelone"),
        ("F", "Bramki stracone"),
        ("G", "Bilans"),
    )
    _add_row(data, 4, [(col, label, 4, None) for col, label in headers])

    last_team_row = len(teams) + 4
    home = "'Mecze'!$B$5:$B${}".format(fixture_last_row)
    away = "'Mecze'!$C$5:$C${}".format(fixture_last_row)
    home_score = "'Mecze'!$D$5:$D${}".format(fixture_last_row)
    away_score = "'Mecze'!$E$5:$E${}".format(fixture_last_row)
    home_points = "'Mecze'!$H$5:$H${}".format(fixture_last_row)
    away_points = "'Mecze'!$I$5:$I${}".format(fixture_last_row)
    completed = "'Mecze'!$G$5:$G${}".format(fixture_last_row)
    team_range = "$B$5:$B${}".format(last_team_row)
    points_range = "$D$5:$D${}".format(last_team_row)
    difference_range = "$G$5:$G${}".format(last_team_row)
    goals_for_range = "$E$5:$E${}".format(last_team_row)

    for index, team in enumerate(teams):
        row_number = index + 5
        team_name = team["name"]
        played = (
            '=IF(B{r}="","",SUMIF({h},B{r},{done})+SUMIF({a},B{r},{done}))'
        ).format(r=row_number, h=home, a=away, done=completed)
        goals_for = (
            '=IF(B{r}="","",SUMIF({h},B{r},{hs})+SUMIF({a},B{r},{as}))'
        ).format(r=row_number, h=home, a=away, hs=home_score, **{"as": away_score})
        goals_against = (
            '=IF(B{r}="","",SUMIF({h},B{r},{as})+SUMIF({a},B{r},{hs}))'
        ).format(r=row_number, h=home, a=away, hs=home_score, **{"as": away_score})
        points = (
            '=IF(B{r}="","",SUMIF({h},B{r},{hp})+SUMIF({a},B{r},{ap}))'
        ).format(r=row_number, h=home, a=away, hp=home_points, ap=away_points)
        difference = '=IF(B{r}="","",E{r}-F{r})'.format(r=row_number)
        rank = (
            '=IF(B{r}="","",1+SUMPRODUCT(({teams}<>"")*({pts}>D{r}))'
            '+SUMPRODUCT(({teams}<>"")*({pts}=D{r})*({diff}>G{r}))'
            '+SUMPRODUCT(({teams}<>"")*({pts}=D{r})*({diff}=G{r})*'
            '({gf}>E{r}))+SUMPRODUCT(({teams}<>"")*({pts}=D{r})*'
            '({diff}=G{r})*({gf}=E{r})*({teams}<B{r})))'
        ).format(
            r=row_number,
            teams=team_range,
            pts=points_range,
            diff=difference_range,
            gf=goals_for_range,
        )
        _add_row(
            data,
            row_number,
            [
                ("A", None, 5, rank),
                ("B", team_name, 3, None),
                ("C", None, 5, played),
                ("D", None, 5, points),
                ("E", None, 5, goals_for),
                ("F", None, 5, goals_against),
                ("G", None, 5, difference),
            ],
        )
    _add_merge(root, ["A1:G1", "A2:G2"])
    _add_filter(root, "A4:G{}".format(last_team_row))
    return root


def _sheet_fixtures(matches, teams):
    root = ET.Element(_tag("worksheet"))
    _add_sheet_views(root, 4)
    _add_columns(root, [12, 30, 30, 20, 20, 26, 12, 12, 12], hidden=(7, 8, 9))
    data = ET.SubElement(root, _tag("sheetData"))
    _add_row(data, 1, [("A", "Terminarz i wyniki", 1, None)])
    _add_row(
        data,
        2,
        [
            (
                "A",
                "Zmień wyniki w żółtych komórkach. Zmiany dotyczą tylko tego skoroszytu "
                "i nie zapisują się w aplikacji ani jej bazie danych.",
                2,
                None,
            )
        ],
    )
    headers = (
        ("A", "Kolejka"),
        ("B", "Gospodarze"),
        ("C", "Goście"),
        ("D", "Bramki gospodarzy"),
        ("E", "Bramki gości"),
        ("F", "Pauzuje"),
    )
    _add_row(data, 4, [(col, label, 4, None) for col, label in headers])

    team_names = {team["id"]: team["name"] for team in teams}
    grouped = {}
    for match in matches:
        grouped.setdefault(match["round_number"], []).append(match)
    row_number = 5
    for round_number in sorted(grouped):
        round_matches = grouped[round_number]
        for match in round_matches:
            _add_row(
                data,
                row_number,
                [
                    ("A", round_number, 5, None),
                    ("B", match["home_name"], 3, None),
                    ("C", match["away_name"], 3, None),
                    ("D", match["home_score"], 6, None),
                    ("E", match["away_score"], 6, None),
                    ("F", None, 3, None),
                    ("G", None, 0, '=IF(AND(ISNUMBER(D{r}),ISNUMBER(E{r})),1,"")'.format(r=row_number)),
                    ("H", None, 0, '=IF(G{r}="","",IF(D{r}>E{r},3,IF(D{r}=E{r},1,0)))'.format(r=row_number)),
                    ("I", None, 0, '=IF(G{r}="","",IF(E{r}>D{r},3,IF(E{r}=D{r},1,0)))'.format(r=row_number)),
                ],
            )
            row_number += 1
        playing = {
            team_id
            for match in round_matches
            for team_id in (match["home_team_id"], match["away_team_id"])
        }
        byes = [team_names[team_id] for team_id in team_names if team_id not in playing]
        for bye in byes:
            _add_row(
                data,
                row_number,
                [
                    ("A", round_number, 5, None),
                    ("B", None, 3, None),
                    ("C", None, 3, None),
                    ("D", None, 3, None),
                    ("E", None, 3, None),
                    ("F", "Pauzuje: " + bye, 3, None),
                    ("G", None, 0, None),
                    ("H", None, 0, None),
                    ("I", None, 0, None),
                ],
            )
            row_number += 1

    last_row = row_number - 1
    _add_merge(root, ["A1:F1", "A2:F2"])
    _add_filter(root, "A4:F{}".format(last_row))
    _add_validation(root, "D5:E{}".format(last_row))
    return root, last_row


def _styles():
    root = ET.Element(_tag("styleSheet"))
    fonts = ET.SubElement(root, _tag("fonts"), {"count": "3"})
    ET.SubElement(fonts, _tag("font"))
    title = ET.SubElement(fonts, _tag("font"))
    ET.SubElement(title, _tag("b"))
    ET.SubElement(title, _tag("sz"), {"val": "16"})
    ET.SubElement(title, _tag("color"), {"rgb": "FFFFFFFF"})
    note = ET.SubElement(fonts, _tag("font"))
    ET.SubElement(note, _tag("i"))
    ET.SubElement(note, _tag("color"), {"rgb": "FF404040"})

    fills = ET.SubElement(root, _tag("fills"), {"count": "4"})
    ET.SubElement(fills, _tag("fill")).append(
        ET.Element(_tag("patternFill"), {"patternType": "none"})
    )
    ET.SubElement(fills, _tag("fill")).append(
        ET.Element(_tag("patternFill"), {"patternType": "gray125"})
    )
    for color in ("FF1F4E78", "FFFFF2CC"):
        fill = ET.SubElement(fills, _tag("fill"))
        pattern = ET.SubElement(fill, _tag("patternFill"), {"patternType": "solid"})
        ET.SubElement(pattern, _tag("fgColor"), {"rgb": color})
        ET.SubElement(pattern, _tag("bgColor"), {"indexed": "64"})

    borders = ET.SubElement(root, _tag("borders"), {"count": "2"})
    ET.SubElement(borders, _tag("border"))
    border = ET.SubElement(borders, _tag("border"))
    for side in ("left", "right", "top", "bottom"):
        ET.SubElement(border, _tag(side), {"style": "thin"}).append(
            ET.Element(_tag("color"), {"rgb": "FFD9E2F3"})
        )

    style_xfs = ET.SubElement(root, _tag("cellStyleXfs"), {"count": "1"})
    ET.SubElement(
        style_xfs,
        _tag("xf"),
        {"numFmtId": "0", "fontId": "0", "fillId": "0", "borderId": "0"},
    )
    formats = ET.SubElement(root, _tag("cellXfs"), {"count": "7"})
    definitions = [
        ("0", "0", "0", "0", None),
        ("1", "2", "0", "0", {"vertical": "center"}),
        ("2", "0", "0", "0", {"wrapText": "1", "vertical": "center"}),
        ("0", "0", "1", "1", None),
        ("0", "2", "1", "1", {"horizontal": "center", "vertical": "center", "wrapText": "1"}),
        ("0", "3", "1", "1", None),
        ("0", "3", "1", "1", {"horizontal": "center"}),
    ]
    for font_id, fill_id, border_id, xf_id, alignment in definitions:
        attributes = {
            "numFmtId": "0",
            "fontId": font_id,
            "fillId": fill_id,
            "borderId": border_id,
            "xfId": xf_id,
        }
        if font_id != "0":
            attributes["applyFont"] = "1"
        if fill_id != "0":
            attributes["applyFill"] = "1"
        if border_id != "0":
            attributes["applyBorder"] = "1"
        cell_format = ET.SubElement(formats, _tag("xf"), attributes)
        if alignment:
            cell_format.set("applyAlignment", "1")
            ET.SubElement(cell_format, _tag("alignment"), alignment)
    styles = ET.SubElement(root, _tag("cellStyles"), {"count": "1"})
    ET.SubElement(
        styles, _tag("cellStyle"), {"name": "Normal", "xfId": "0", "builtinId": "0"}
    )
    return root


def _workbook():
    root = ET.Element(_tag("workbook"))
    sheets = ET.SubElement(root, _tag("sheets"))
    for index, name in enumerate(("Tabela", "Mecze"), start=1):
        ET.SubElement(
            sheets,
            _tag("sheet"),
            {
                "name": name,
                "sheetId": str(index),
                "{{{}}}id".format(REL_NS): "rId{}".format(index),
            },
        )
    ET.SubElement(
        root,
        _tag("calcPr"),
        {"calcMode": "auto", "fullCalcOnLoad": "1", "forceFullCalc": "1"},
    )
    return root


def _content_types():
    root = ET.Element("{{{}}}Types".format(CONTENT_NS))
    for extension, content_type in (
        ("rels", "application/vnd.openxmlformats-package.relationships+xml"),
        ("xml", "application/xml"),
    ):
        ET.SubElement(
            root,
            "{{{}}}Default".format(CONTENT_NS),
            {"Extension": extension, "ContentType": content_type},
        )
    overrides = [
        (
            "/xl/workbook.xml",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml",
        ),
        (
            "/xl/worksheets/sheet1.xml",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
        ),
        (
            "/xl/worksheets/sheet2.xml",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml",
        ),
        (
            "/xl/styles.xml",
            "application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml",
        ),
    ]
    for part_name, content_type in overrides:
        ET.SubElement(
            root,
            "{{{}}}Override".format(CONTENT_NS),
            {"PartName": part_name, "ContentType": content_type},
        )
    return root


def _xml_bytes(element):
    return (
        b'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
        + ET.tostring(element, encoding="utf-8")
    )


def export_league_to_excel(path, league_name, teams, matches):
    """Write a standalone .xlsx snapshot; edits never reach the application's DB."""
    path = Path(path)
    teams = list(teams)
    matches = list(matches)
    if not teams or not matches:
        raise ValueError("Liga nie zawiera drużyn lub zaplanowanych meczów.")

    fixture_sheet, last_fixture_row = _sheet_fixtures(matches, teams)
    standings_sheet = _sheet_standings(teams, last_fixture_row)
    title = standings_sheet.find(".//{}".format(_tag("t")))
    if title is not None:
        title.text = "Tabela ligowa — {}".format(league_name)

    sheets_order = {
        "sheetViews": 0,
        "cols": 1,
        "sheetData": 2,
        "autoFilter": 3,
        "mergeCells": 4,
        "dataValidations": 5,
    }
    for sheet in (standings_sheet, fixture_sheet):
        sheet[:] = sorted(
            sheet,
            key=lambda child: sheets_order.get(child.tag.rsplit("}", 1)[-1], 99),
        )

    package_relationships = ET.Element("{{{}}}Relationships".format(PKG_REL_NS))
    ET.SubElement(
        package_relationships,
        "{{{}}}Relationship".format(PKG_REL_NS),
        {
            "Id": "rId1",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument",
            "Target": "xl/workbook.xml",
        },
    )
    workbook_relationships = ET.Element("{{{}}}Relationships".format(PKG_REL_NS))
    for index in range(1, 3):
        ET.SubElement(
            workbook_relationships,
            "{{{}}}Relationship".format(PKG_REL_NS),
            {
                "Id": "rId{}".format(index),
                "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet",
                "Target": "worksheets/sheet{}.xml".format(index),
            },
        )
    ET.SubElement(
        workbook_relationships,
        "{{{}}}Relationship".format(PKG_REL_NS),
        {
            "Id": "rId3",
            "Type": "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles",
            "Target": "styles.xml",
        },
    )

    files = {
        "[Content_Types].xml": _content_types(),
        "_rels/.rels": package_relationships,
        "xl/workbook.xml": _workbook(),
        "xl/_rels/workbook.xml.rels": workbook_relationships,
        "xl/styles.xml": _styles(),
        "xl/worksheets/sheet1.xml": standings_sheet,
        "xl/worksheets/sheet2.xml": fixture_sheet,
    }
    with zipfile.ZipFile(str(path), "w", zipfile.ZIP_DEFLATED) as workbook:
        for name, element in files.items():
            workbook.writestr(name, _xml_bytes(element))
    return path
