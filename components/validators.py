"""
Componentes de validación visual
"""
import streamlit as st
from dataclasses import dataclass


@dataclass
class ValidationResult:
    """Resultado de validación"""
    is_valid: bool
    issues: list[str]
    warnings: list[str]
    metrics: dict


def DisplayValidation(result: ValidationResult):
    """
    Renderiza resultados de validación con colores.
    
    Args:
        result: ValidationResult con issues/warnings
    """
    col1, col2, col3 = st.columns(3)
    
    with col1:
        status = "✅ Válido" if result.is_valid else "❌ Inválido"
        color = "#10B981" if result.is_valid else "#EF4444"
        st.markdown(f"<h3 style='color: {color}'>{status}</h3>", 
                   unsafe_allow_html=True)
    
    with col2:
        if result.warnings:
            st.warning(f"⚠️ {len(result.warnings)} advertencias")
    
    with col3:
        if result.issues:
            st.error(f"❌ {len(result.issues)} errores")
    
    # Mostrar detalles
    if result.issues:
        st.markdown("**Errores:**")
        for issue in result.issues:
            st.markdown(f"- ❌ {issue}")
    
    if result.warnings:
        st.markdown("**Advertencias:**")
        for warning in result.warnings:
            st.markdown(f"- ⚠️ {warning}")
    
    # Métricas
    if result.metrics:
        st.markdown("**Métricas:**")
        metric_cols = st.columns(len(result.metrics))
        for i, (label, value) in enumerate(result.metrics.items()):
            with metric_cols[i]:
                st.metric(label, value)