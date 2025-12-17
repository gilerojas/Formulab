"""
Test de las funciones matemáticas principales (Formulab Core)
Verifica consistencia de cálculos físicos.
"""

import pandas as pd
from formulab.core.engine.escalado_core import (
    calcular_escalado,
    validar_formula_escalada,
    calcular_pg,
)

def test_escalado_and_validations():
    # Simula una fórmula simple
    df = pd.DataFrame({
        "nombre": ["AGUA", "RESINA"],
        "CANT": [12.0, 25.0],
        "Densidad_KG_GL": [3.78, 4.20],
    })

    gal_objetivo = 25.0
    pg_pintura = 5.46

    df_escalado = calcular_escalado(df, gal_objetivo, pg_pintura)

    # Σ(GL_PRO) debe ser ≈ gal_objetivo
    suma_glpro = df_escalado["GL_PRO"].sum()
    assert abs(suma_glpro - gal_objetivo) < 0.2

    # Σ(KG_PRO) debe escalar correctamente
    assert all(df_escalado["KG_PRO"] > 0)

    # Validaciones
    valid, issues, metrics = validar_formula_escalada(df_escalado, gal_objetivo, pg_pintura)
    assert isinstance(valid, bool)
    assert "suma_glpro" in metrics

def test_calcular_pg():
    df = pd.DataFrame({"KG": [10, 20], "GL": [2, 4]})
    pg = calcular_pg(df)
    assert round(pg, 2) == 5.00
