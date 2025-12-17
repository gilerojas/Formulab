"""
Tablas y dataframes customizados
"""
import streamlit as st
import pandas as pd


def FormulaTable(df: pd.DataFrame, selectable: bool = False):
    """
    Renderiza tabla de fórmulas con interactividad.
    
    Args:
        df: DataFrame con columnas: formula_key, tipo, color, p_g
        selectable: Si permite seleccionar filas
        
    Returns:
        Clave de fórmula seleccionada (si selectable=True)
    """
    if df.empty:
        st.info("📚 No hay fórmulas disponibles")
        return None
    
    # Preparar columnas display
    display_df = df[["formula_key", "tipo", "color", "p_g"]].copy()
    display_df.columns = ["Formula Key", "Tipo", "Color", "P/G (kg/gal)"]
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=300,
        key="formula_table"
    )
    
    if selectable:
        selected_key = st.selectbox(
            "Selecciona una fórmula:",
            options=df["formula_key"].tolist(),
            key="formula_selector"
        )
        return selected_key
    
    return None


def IngredientsTable(df: pd.DataFrame, title: str = "Ingredientes"):
    """
    Renderiza tabla de ingredientes con formato profesional.
    
    Args:
        df: DataFrame con columnas: codigo, nombre, cant, unidad, kg_gl
        title: Título de la tabla
    """
    st.subheader(title)
    
    if df.empty:
        st.warning("⚠️ Sin ingredientes")
        return
    
    # Formatear para display
    display_df = df.copy()
    display_df.columns = ["Código", "Nombre", "Cantidad", "Unidad", "KG/GL"]
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=200,
        key="ingredients_table"
    )
    
    # Resumen al pie
    col1, col2 = st.columns(2)
    with col1:
        st.metric("Total Ingredientes", len(df))
    with col2:
        total_kg = df["cant"].sum()
        st.metric("Total KG", f"{total_kg:.2f}")


def ComparisonTable(df_base: pd.DataFrame, df_escalado: pd.DataFrame, 
                   factor: float):
    """
    Tabla comparativa base vs escalado lado a lado.
    
    Args:
        df_base: Ingredientes a 100%
        df_escalado: Ingredientes escalados
        factor: Factor de escala (ej: 0.25 para 25 gal de 100)
    """
    st.subheader(f"📊 Comparación: Base → Escalado ({factor*100:.0f}%)")
    
    comparison = pd.DataFrame({
        "Ingrediente": df_base["nombre"],
        "KG Base": df_base["cant"],
        "KG Producir": df_escalado["cant"],
        "Diferencia": df_escalado["cant"] - df_base["cant"]
    })
    
    st.dataframe(
        comparison,
        use_container_width=True,
        height=250,
        key="comparison_table"
    )