import tempfile
import unittest
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from excel_export import export_league_to_excel
from main import connect_database, create_league, get_rounds, record_result


MAIN_NS = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
NS = {"x": MAIN_NS}


class ExcelExportTests(unittest.TestCase):
    def test_export_is_a_standalone_snapshot_with_editable_score_cells(self):
        with tempfile.TemporaryDirectory() as directory:
            database = connect_database(Path(directory) / "league.db")
            try:
                league_id = create_league(
                    database, "Liga testowa", ["Orły", "Lisy", "Wilki"]
                )
                match = get_rounds(database, league_id)[0]
                record_result(database, match["id"], 2, 1)
                teams = database.execute(
                    "SELECT id, name FROM app_teams WHERE league_id = ? ORDER BY id",
                    (league_id,),
                ).fetchall()
                matches = get_rounds(database, league_id)
                export_path = Path(directory) / "export.xlsx"

                export_league_to_excel(
                    export_path, "Liga testowa", teams, matches
                )

                saved_result = database.execute(
                        "SELECT home_score, away_score FROM app_matches WHERE id = ?",
                        (match["id"],),
                    ).fetchone()
                self.assertEqual(
                    (saved_result["home_score"], saved_result["away_score"]), (2, 1)
                )
                with zipfile.ZipFile(str(export_path)) as workbook:
                    self.assertEqual(
                        set(workbook.namelist()),
                        {
                            "[Content_Types].xml",
                            "_rels/.rels",
                            "xl/workbook.xml",
                            "xl/_rels/workbook.xml.rels",
                            "xl/styles.xml",
                            "xl/worksheets/sheet1.xml",
                            "xl/worksheets/sheet2.xml",
                        },
                    )
                    for name in workbook.namelist():
                        if name.endswith(".xml") or name.endswith(".rels"):
                            ET.fromstring(workbook.read(name))

                    standings = ET.fromstring(
                        workbook.read("xl/worksheets/sheet1.xml")
                    )
                    formulas = [
                        cell.find("x:f", NS).text
                        for cell in standings.findall(".//x:c[x:f]", NS)
                    ]
                    self.assertTrue(any("SUMPRODUCT" in formula for formula in formulas))
                    self.assertTrue(any("SUMIF" in formula for formula in formulas))
                    standings_cells = {
                        cell.attrib["r"]: cell
                        for cell in standings.findall(".//x:c", NS)
                    }
                    self.assertEqual(
                        [
                            standings_cells["B{}".format(row)].find("x:is/x:t", NS).text
                            for row in range(5, 8)
                        ],
                        ["Orły", "Lisy", "Wilki"],
                    )
                    self.assertFalse(
                        any(
                            "<sqlite3.Row" in (cell.find("x:is/x:t", NS).text or "")
                            for cell in standings_cells.values()
                            if cell.find("x:is/x:t", NS) is not None
                        )
                    )

                    fixtures = ET.fromstring(
                        workbook.read("xl/worksheets/sheet2.xml")
                    )
                    cells = {
                        cell.attrib["r"]: cell
                        for cell in fixtures.findall(".//x:c", NS)
                    }
                    self.assertIn("ISNUMBER(D5)", cells["G5"].find("x:f", NS).text)
                    self.assertIn("D5>E5", cells["H5"].find("x:f", NS).text)
                    self.assertIn("E5>D5", cells["I5"].find("x:f", NS).text)
                    hidden_columns = fixtures.findall(".//x:cols/x:col", NS)
                    self.assertTrue(
                        all(column.attrib.get("hidden") == "1" for column in hidden_columns[-3:])
                    )
                    first_match = matches[0]
                    match_row = next(
                        row
                        for row in range(5, 5 + len(matches) + 3)
                        if cells.get("B{}".format(row)) is not None
                        and cells["B{}".format(row)].find("x:is/x:t", NS) is not None
                        and cells["B{}".format(row)].find("x:is/x:t", NS).text
                        == first_match["home_name"]
                    )
                    self.assertEqual(
                        cells["D{}".format(match_row)].find("x:v", NS).text, "2"
                    )
                    self.assertEqual(
                        cells["E{}".format(match_row)].find("x:v", NS).text, "1"
                    )
                    self.assertEqual(
                        cells["D{}".format(match_row)].attrib["s"], "6"
                    )
            finally:
                database.close()


if __name__ == "__main__":
    unittest.main()
