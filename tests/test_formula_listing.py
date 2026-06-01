from formulab.sheets import formulas_manager


def test_listar_formulas_normalizes_filters(monkeypatch):
    rows = [
        [
            "Formula_Key",
            "Marca",
            "Tipo",
            "Color",
            "Volumen_Base",
            "PG_Pintura",
            "Total_Ingredientes",
            "Fecha_Creacion",
            "Observaciones",
            "Estatus",
        ],
        [" IN-SLT-GRIS26NEW ", " infiniti ", " Sellador ", "Gris", "25", "4.95", "21", "", "", " activa "],
        ["PM-HP-BLANCO", "MILAN", "HP", "Blanco", "100", "5.4", "10", "", "", "ACTIVA"],
        ["IN-SLT-OLD", "INFINITI", "Sellador", "Vieja", "75", "4.9", "21", "", "", "INACTIVA"],
    ]

    monkeypatch.setattr(formulas_manager, "read_sheet", lambda sheet_name: rows)

    df = formulas_manager.listar_formulas(marca="INFINITI", estatus="ACTIVA")

    assert df["Formula_Key"].tolist() == ["IN-SLT-GRIS26NEW"]
    assert df["Marca"].tolist() == ["infiniti"]
    assert df["Estatus"].tolist() == ["activa"]
