import pandas as pd

from formulab.sheets import formulas_manager


def test_guardar_formula_aborts_when_lookup_fails(monkeypatch):
    result = {
        "meta": {
            "marca": "INFINITI",
            "tipo": "SELLADOR TECHOS HP",
            "color": "Verde",
            "gal_producir": 200,
            "P/G": 4.82,
        },
        "formula_key": "IN-SLP-VERDEAPLITEC",
        "df_escalado": pd.DataFrame(
            [
                {
                    "CODIGO": "SV-0001",
                    "nombre": "AGUA",
                    "CANT": 10,
                    "Densidad_KG_GL": 3.78,
                    "KG_PRO": 1,
                    "GL_PRO": 1,
                    "etapa": "Mezcla",
                }
            ]
        ),
    }

    def fail_lookup(*args, **kwargs):
        raise RuntimeError("quota")

    appended = []
    monkeypatch.setattr(formulas_manager, "buscar_formula", fail_lookup)
    monkeypatch.setattr(formulas_manager, "append_sheet", lambda *args: appended.append(args))

    formula_key, success = formulas_manager.guardar_formula(result)

    assert formula_key == "IN-SLP-VERDEAPLITEC"
    assert success is False
    assert appended == []
