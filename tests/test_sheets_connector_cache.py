from formulab.sheets import sheets_connector


class FakeWorksheet:
    def __init__(self):
        self.get_all_values_calls = 0
        self.appended = []

    def get_all_values(self):
        self.get_all_values_calls += 1
        return [["Formula_Key"], ["F-1"]]

    def append_rows(self, values):
        self.appended.extend(values)


def test_read_sheet_uses_process_cache(monkeypatch):
    worksheet = FakeWorksheet()
    sheets_connector.clear_sheet_cache()
    monkeypatch.setattr(sheets_connector, "get_worksheet", lambda *args, **kwargs: worksheet)

    first = sheets_connector.read_sheet("GREQ_Formulas")
    second = sheets_connector.read_sheet("GREQ_Formulas")

    assert first == second
    assert worksheet.get_all_values_calls == 1


def test_append_sheet_invalidates_read_cache(monkeypatch):
    worksheet = FakeWorksheet()
    sheets_connector.clear_sheet_cache()
    monkeypatch.setattr(sheets_connector, "get_worksheet", lambda *args, **kwargs: worksheet)

    sheets_connector.read_sheet("GREQ_Formulas")
    sheets_connector.append_sheet("GREQ_Formulas", ["F-2"])
    sheets_connector.read_sheet("GREQ_Formulas")

    assert worksheet.appended == [["F-2"]]
    assert worksheet.get_all_values_calls == 2
