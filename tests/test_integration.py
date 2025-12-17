"""
Test de integración del pipeline completo (procesar_formula)
Asegura que parser + escalado + validación funcionan en conjunto.
"""

from formulab.formulab_api import procesar_formula

def test_pipeline_full_execution():
    raw = """ACRILICA SUPERIOR VOLUMEN P/G
BLANCO 100-66 21.33 5.46
CODIGO NOMBRE GENERICO CANT UNIDAD KG/GL
SV-0001 AGUA 12.00 KG 3.78
RV-0002 RESINA 25.00 KG 4.20
TOTAL 100 21.33"""

    result = procesar_formula(raw, gal_objetivo=25)

    # Estructura del resultado
    assert "meta" in result
    assert "df_escalado" in result
    assert "valid" in result

    # Debe calcular gal_objetivo correctamente
    resumen = result["resumen"]
    assert round(resumen["gal_objetivo"], 2) == 25.00
    assert resumen["total_ingredientes"] >= 2

    # DataFrame escalado coherente
    df_escalado = result["df_escalado"]
    assert "KG_PRO" in df_escalado.columns
    assert "GL_PRO" in df_escalado.columns
