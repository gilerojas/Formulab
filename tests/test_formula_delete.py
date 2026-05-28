from formulab.sheets import formulas_manager


def test_delete_impact_uses_exact_formula_key(monkeypatch):
    def fake_find(sheet_name, column_index, value):
        assert column_index == 0
        assert value == "IN-SLT-GRIS26"
        if sheet_name == "GREQ_Formulas":
            return [12]
        if sheet_name == "Formulas_Detalle":
            return [101, 102, 103]
        return []

    monkeypatch.setattr(formulas_manager, "find_row_indices_by_value", fake_find)

    impacto = formulas_manager.obtener_impacto_eliminacion_formula(" IN-SLT-GRIS26 ")

    assert impacto["can_delete"] is True
    assert impacto["formula_rows"] == [12]
    assert impacto["detalle_rows"] == [101, 102, 103]


def test_delete_formula_requires_exact_confirmation(monkeypatch):
    deleted = []
    monkeypatch.setattr(formulas_manager, "delete_rows", lambda *args: deleted.append(args))

    success, message, impacto = formulas_manager.eliminar_formula(
        "IN-SLT-GRIS26",
        "IN-SLT-GRIS26NEW",
    )

    assert success is False
    assert "no coincide" in message
    assert impacto == {}
    assert deleted == []


def test_delete_formula_deletes_rows_bottom_up(monkeypatch):
    monkeypatch.setattr(
        formulas_manager,
        "obtener_impacto_eliminacion_formula",
        lambda formula_key: {
            "formula_key": formula_key,
            "formula_rows": [7],
            "detalle_rows": [20, 18, 19],
            "can_delete": True,
            "reason": "",
        },
    )

    deleted = []
    monkeypatch.setattr(formulas_manager, "delete_rows", lambda *args: deleted.append(args))

    success, message, impacto = formulas_manager.eliminar_formula(
        "IN-SLT-GRIS26",
        "IN-SLT-GRIS26",
    )

    assert success is True
    assert "correctamente" in message
    assert impacto["formula_rows"] == [7]
    assert deleted == [
        ("Formulas_Detalle", 20),
        ("Formulas_Detalle", 19),
        ("Formulas_Detalle", 18),
        ("GREQ_Formulas", 7),
    ]


def test_delete_formula_blocks_ambiguous_formula_rows(monkeypatch):
    monkeypatch.setattr(
        formulas_manager,
        "find_row_indices_by_value",
        lambda sheet_name, column_index, value: [3, 8] if sheet_name == "GREQ_Formulas" else [30],
    )

    deleted = []
    monkeypatch.setattr(formulas_manager, "delete_rows", lambda *args: deleted.append(args))

    success, message, impacto = formulas_manager.eliminar_formula(
        "IN-SLT-GRIS26",
        "IN-SLT-GRIS26",
    )

    assert success is False
    assert "más de una fila" in message
    assert impacto["formula_rows"] == [3, 8]
    assert deleted == []
