"""
Test básico del parser de fórmulas (Formulab)
Valida detección de metadata y estructura del DataFrame.
"""

from formulab.core.parser.parser_formula import parse_text_to_df

def test_parser_detects_metadata_and_ingredients():
    raw = """ACRILICA SUPERIOR VOLUMEN P/G
BLANCO 100-66 21.33 5.46
CODIGO NOMBRE GENERICO CANT UNIDAD KG/GL
SV-0001 AGUA 12.00 KG 3.78
RV-0002 RESINA 25.00 KG 4.20
TOTAL 100 21.33"""

    meta, fkey, df = parse_text_to_df(raw, brand_code="PM")

    # Validar metadatos clave
    assert meta["tipo"].startswith("Acrilica")
    assert "Blanco" in meta["color"]
    assert round(meta["Volumen"], 2) == 21.33
    assert round(meta["P/G"], 2) == 5.46

    # DataFrame debe tener al menos 2 ingredientes
    assert len(df) >= 2
    assert "CANT" in df.columns
    assert "Densidad (KG/GL)" in df.columns
