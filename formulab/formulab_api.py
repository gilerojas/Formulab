"""
Formulab Core API - v2.0
-----------------------
Puente entre parser y motor de escalamiento para el sistema GREQ.
Soporte para tipo_override desde Streamlit.
"""
from formulab.core.parser.parser_formula import parse_text_to_df
from formulab.core.engine.escalado_core import (
    calcular_escalado,
    validar_formula_escalada,
    calcular_pg,
    generar_resumen,
)
import pandas as pd

def procesar_formula(
    raw_text: str,
    gal_objetivo: float,
    marca: str = None,
    tipo_override: str = None  # 🆕 NUEVO PARÁMETRO
):
    """
    Pipeline completo: parsea texto → escala fórmula → valida consistencia.
    
    Args:
        raw_text (str): Texto crudo de fórmula
        gal_objetivo (float): Galones a producir
        marca (str): INFINITI o MILAN
        tipo_override (str): Tipo manual desde dropdown (ej: "ACRILICA SUPERIOR HP")
    
    Returns:
        dict: Resultado completo con meta, df_escalado, validación
    """
    # Determinar brand_code
    brand_code = None
    if marca:
        marca_upper = marca.upper()
        brand_code = "IN" if marca_upper == "INFINITI" else "PM"
    
    # 🆕 PASAR TIPO_OVERRIDE AL PARSER
    meta, fkey, df_base = parse_text_to_df(
        raw_text,
        brand_code=brand_code,
        tipo_override=tipo_override  # ← CRÍTICO
    )
    
    # Agregar marca al metadata
    if marca:
        meta["marca"] = marca

    # Renombrar columnas para el motor de escalado
    df_ingredientes = df_base.rename(columns={
        "Nombre": "nombre",
        "Densidad (KG/GL)": "Densidad_KG_GL"
    })
    
    # Eliminar columnas viejas del parser
    cols_to_drop = [col for col in df_ingredientes.columns if col in ["KG/PRO", "GL/PRO"]]
    if cols_to_drop:
        df_ingredientes = df_ingredientes.drop(columns=cols_to_drop)

    # Calcular escalado
    df_escalado = calcular_escalado(
        ingredientes_df=df_ingredientes,
        gal_objetivo=gal_objetivo,
        pg_pintura=meta["P/G"]
    )

    # Validar
    is_valid, issues, metrics = validar_formula_escalada(
        df_escalado, gal_objetivo, meta["P/G"]
    )

    resumen = generar_resumen(df_escalado, gal_objetivo, meta["gal_producir"])

    return {
        "meta": meta,
        "formula_key": fkey,
        "df_escalado": df_escalado,
        "valid": is_valid,
        "issues": issues,
        "metrics": metrics,
        "resumen": resumen
    }

def ajustar_etapas_finales(df):
    """Asigna Mezcla final a ingredientes después de última etapa"""
    if "etapa" not in df.columns or len(df) == 0:
        return df
    
    # Índice de última dispersión/disolución
    ultima_etapa_idx = -1
    for idx in range(len(df) - 1, -1, -1):
        etapa = df.iloc[idx]["etapa"]
        if "Dispersión" in etapa or "Disolución" in etapa:
            ultima_etapa_idx = idx
            break
    
    # Todo después → mezcla final
    if ultima_etapa_idx >= 0:
        for idx in range(ultima_etapa_idx + 1, len(df)):
            if df.iloc[idx]["etapa"] == "Preparación base":
                df.at[idx, "etapa"] = "Mezcla final (2–3 min)"
    
    return df