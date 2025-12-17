# -*- coding: utf-8 -*-
"""
GREQ - Funciones Core para Escalamiento de Fórmulas
Versión: 1.0
Autor: Sistema GREQ
"""

import pandas as pd
import numpy as np
from typing import Tuple, List, Dict

# ==================== FUNCIÓN PRINCIPAL ====================

def calcular_escalado(
    ingredientes_df: pd.DataFrame,
    gal_objetivo: float,
    pg_pintura: float
) -> pd.DataFrame:
    """
    Calcula valores escalados de una fórmula según galones objetivo.
    
    MATEMÁTICA:
    - CANT, Densidad_KG_GL: CONSTANTES (no cambian)
    - KG = CANT (siempre)
    - GL = KG / Densidad_KG_GL
    - KG_PRO = (CANT * gal_objetivo * P/G) / Total_KG
    - GL_PRO = (GL * gal_objetivo) / Total_GL
    
    Args:
        ingredientes_df: DataFrame con columnas ['nombre', 'CANT', 'Densidad_KG_GL']
        gal_objetivo: Galones a producir (ej: 25, 100, 0.75)
        pg_pintura: P/G de la pintura final (ej: 5.46)
    
    Returns:
        DataFrame con columnas escaladas: 
        ['nombre', 'CANT', 'Densidad_KG_GL', 'KG', 'GL', 'KG_PRO', 'GL_PRO']
    
    Raises:
        ValueError: Si datos inválidos o inconsistentes
    
    Example:
        >>> ing_df = pd.DataFrame({
        ...     'nombre': ['AGUA', 'RESINA'],
        ...     'CANT': [12.00, 25.00],
        ...     'Densidad_KG_GL': [3.778, 3.90]
        ... })
        >>> resultado = calcular_escalado(ing_df, gal_objetivo=25, pg_pintura=5.46)
        >>> resultado['GL_PRO'].sum()  # Debe ser ≈ 25.00
    """
    
    # Validaciones de entrada
    if ingredientes_df.empty:
        raise ValueError("DataFrame de ingredientes está vacío")
    
    if gal_objetivo <= 0:
        raise ValueError(f"gal_objetivo debe ser > 0, recibido: {gal_objetivo}")
    
    if pg_pintura <= 0:
        raise ValueError(f"pg_pintura debe ser > 0, recibido: {pg_pintura}")
    
    required_cols = ['nombre', 'CANT', 'Densidad_KG_GL']
    missing = set(required_cols) - set(ingredientes_df.columns)
    if missing:
        raise ValueError(f"Columnas faltantes en DataFrame: {missing}")
    
    # Crear copia para no modificar original
    df = ingredientes_df.copy()
    
    # ==================== CÁLCULOS CONSTANTES ====================
    
    # KG siempre igual a CANT
    df['KG'] = df['CANT']
    
    # GL = KG / Densidad
    df['GL'] = df['KG'] / df['Densidad_KG_GL']
    
    # Totales (necesarios para proporciones)
    total_kg = df['KG'].sum()
    total_gl = df['GL'].sum()
    
    # Validación: totales deben ser positivos
    if total_kg <= 0:
        raise ValueError(f"Total KG inválido: {total_kg}")
    if total_gl <= 0:
        raise ValueError(f"Total GL inválido: {total_gl}")
    
    # ==================== CÁLCULOS ESCALADOS ====================
    
    # KG/PRO = (CANT * gal_objetivo * P/G) / Total_KG
    df['KG_PRO'] = (df['CANT'] * gal_objetivo * pg_pintura) / total_kg
    
    # GL/PRO = (GL * gal_objetivo) / Total_GL
    df['GL_PRO'] = (df['GL'] * gal_objetivo) / total_gl
    
    # Redondear a 2 decimales para limpieza
    df['KG'] = df['KG'].round(2)
    df['GL'] = df['GL'].round(2)
    df['KG_PRO'] = df['KG_PRO'].round(2)
    df['GL_PRO'] = df['GL_PRO'].round(2)
    
    return df


# ==================== VALIDACIÓN ====================

def validar_formula_escalada(
    df: pd.DataFrame,
    gal_objetivo: float,
    pg_esperado: float,
    tolerancia_cant: float = 1.0,
    tolerancia_gal: float = 0.05,
    tolerancia_pg: float = 0.5
) -> Tuple[bool, List[str], Dict[str, float]]:
    """
    Valida consistencia física de una fórmula escalada.

    CHECKS CRÍTICOS:
    1. Σ(CANT) ≈ 100 ± tolerancia_cant
    2. Σ(GL_PRO) ≈ gal_objetivo ± tolerancia_gal
    3. P/G calculado ≈ P/G esperado ± tolerancia_pg

    Args:
        df: DataFrame con fórmula escalada
        gal_objetivo: Galones solicitados
        pg_esperado: P/G de la fórmula maestra
        tolerancia_cant: % de error aceptable en suma CANT (default: 1.0%)
        tolerancia_gal: Galones de error aceptable (default: 0.05)
        tolerancia_pg: Error aceptable en P/G (default: 0.5)

    Returns:
        Tuple (is_valid, issues, metrics)
    """
    issues = []
    metrics = {}

    # ==================== CHECK 1: Suma CANT ====================
    suma_cant = float(df["CANT"].sum())
    metrics["suma_cant"] = round(suma_cant, 3)

    if abs(suma_cant - 100.0) > tolerancia_cant:
        issues.append(
            f"⚠️  Suma CANT = {suma_cant:.2f}% (esperado 100.00% ± {tolerancia_cant}%)"
        )

    # ==================== CHECK 2: Suma GL/PRO ====================
    suma_glpro = float(df["GL_PRO"].sum())
    metrics["suma_glpro"] = round(suma_glpro, 3)

    diff_gal = abs(suma_glpro - gal_objetivo)
    if diff_gal > tolerancia_gal:
        issues.append(
            f"⚠️  Suma GL/PRO = {suma_glpro:.2f} gal (esperado {gal_objetivo:.2f} ± {tolerancia_gal})"
        )

    # ==================== CHECK 3: P/G Calculado ====================
    total_kg = float(df["KG"].sum())
    total_gl = float(df["GL"].sum())

    if total_gl > 0:
        pg_calculado = total_kg / total_gl
        metrics["pg_calculado"] = round(pg_calculado, 3)
        diff_pg = abs(pg_calculado - pg_esperado)
        if diff_pg > tolerancia_pg:
            issues.append(
                f"⚠️  P/G calculado = {pg_calculado:.2f} (esperado {pg_esperado:.2f} ± {tolerancia_pg})"
            )
    else:
        issues.append("❌ Total GL = 0, no se puede calcular P/G")
        metrics["pg_calculado"] = None

    # ==================== CHECK 4: Valores válidos ====================
    if df["KG_PRO"].isna().any() or (df["KG_PRO"] < 0).any():
        issues.append("❌ Valores inválidos detectados en KG_PRO")

    if df["GL_PRO"].isna().any() or (df["GL_PRO"] < 0).any():
        issues.append("❌ Valores inválidos detectados en GL_PRO")

    # ==================== RESULTADO ====================
    is_valid = len(issues) == 0
    return is_valid, issues, metrics

    
    # ==================== CHECK 1: Suma CANT ====================
    suma_cant = df['CANT'].sum()
    metrics['suma_cant'] = suma_cant
    
    if abs(suma_cant - 100.0) > tolerancia_cant:
        issues.append(
            f"⚠️  Suma CANT = {suma_cant:.2f}% (esperado 100.00% ± {tolerancia_cant}%)"
        )
    
    # ==================== CHECK 2: Suma GL/PRO ====================
    suma_glpro = df['GL_PRO'].sum()
    metrics['suma_glpro'] = suma_glpro
    
    diff_gal = abs(suma_glpro - gal_objetivo)
    if diff_gal > tolerancia_gal:
        issues.append(
            f"⚠️  Suma GL/PRO = {suma_glpro:.2f} gal (esperado {gal_objetivo:.2f} ± {tolerancia_gal})"
        )
    
    # ==================== CHECK 3: P/G Calculado ====================
    total_kg = df['KG'].sum()
    total_gl = df['GL'].sum()
    
    if total_gl > 0:
        pg_calculado = total_kg / total_gl
        metrics['pg_calculado'] = pg_calculado
        
        diff_pg = abs(pg_calculado - pg_esperado)
        if diff_pg > tolerancia_pg:
            issues.append(
                f"⚠️  P/G calculado = {pg_calculado:.2f} (esperado {pg_esperado:.2f} ± {tolerancia_pg})"
            )
    else:
        issues.append("❌ Total GL = 0, no se puede calcular P/G")
        metrics['pg_calculado'] = None
    
    # ==================== CHECK 4: Valores válidos ====================
    # Solo validar columnas con guion bajo (las nuevas)
    cols_to_check = [col for col in df.columns if col in ["KG_PRO", "GL_PRO"]]

    for col in cols_to_check:
        if df[col].isna().any():
            issues.append(f"❌ Valores NaN detectados en {col}")
        
        # Permitir exactamente 0, rechazar negativos
        if (df[col] < -0.001).any():  # Tolerancia por redondeo
            issues.append(f"❌ Valores negativos detectados en {col}")


# ==================== HELPER: Calcular P/G ====================

def calcular_pg(df: pd.DataFrame) -> float:
    """
    Calcula P/G a partir de totales KG y GL.
    
    Args:
        df: DataFrame con columnas 'KG' y 'GL'
    
    Returns:
        P/G calculado (Total_KG / Total_GL)
    
    Raises:
        ValueError: Si Total_GL es 0
    """
    total_kg = df['KG'].sum()
    total_gl = df['GL'].sum()
    
    if total_gl == 0:
        raise ValueError("Total GL es 0, no se puede calcular P/G")
    
    return total_kg / total_gl


# ==================== HELPER: Resumen de Fórmula ====================

def generar_resumen(
    df: pd.DataFrame,
    gal_objetivo: float,
    gal_base: float
) -> Dict[str, any]:
    """
    Genera resumen ejecutivo de una fórmula escalada.
    
    Args:
        df: DataFrame con fórmula escalada
        gal_objetivo: Galones solicitados
        gal_base: Galones de la fórmula maestra
    
    Returns:
        Dict con métricas clave para display
    """
    total_kg = df['KG'].sum()
    total_gl = df['GL'].sum()
    total_kg_pro = df['KG_PRO'].sum()
    total_gl_pro = df['GL_PRO'].sum()
    
    factor = gal_objetivo / gal_base if gal_base > 0 else 0
    
    return {
        'gal_base': gal_base,
        'gal_objetivo': gal_objetivo,
        'factor_escala': factor,
        'total_ingredientes': len(df),
        'suma_cant': df['CANT'].sum(),
        'total_kg_constante': total_kg,
        'total_gl_constante': total_gl,
        'total_kg_producir': total_kg_pro,
        'total_gl_producir': total_gl_pro,
        'pg_calculado': total_kg / total_gl if total_gl > 0 else None
    }