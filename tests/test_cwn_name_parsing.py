import csv
import io
from types import SimpleNamespace

from cogs.sheets import CharacterSheetCog


def test_cwn_standard_sheet_reads_name_from_b4():
    rows = [["Cities Without Number Character Sheet"]]
    rows.extend([[] for _ in range(5)])
    rows[3] = ["", "Austin Krow"]
    rows[5] = ["", "Level", "", "1"]
    output = io.StringIO()
    csv.writer(output).writerows(rows)

    cog = CharacterSheetCog(SimpleNamespace(db=None))
    character, error = cog.parse_awn_google_sheet(output.getvalue())

    assert error is None
    assert character["name"] == "Austin Krow"
