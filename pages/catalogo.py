"""
Catálogo de fórmulas - Búsqueda y filtros
"""

import streamlit as st
import pandas as pd
from utils.styling import render_header, apply_custom_css, COLORS

# Importar managers de Sheets
from formulab.sheets.formulas_manager import (
    eliminar_formula,
    listar_formulas,
    obtener_impacto_eliminacion_formula,
    obtener_ingredientes_formula,
)

apply_custom_css()

render_header(
    title="Catálogo de Fórmulas",
    subtitle="Búsqueda, filtros y detalles",
    emoji="📚"
)

st.markdown("---")

# Filtros
st.markdown("### 🔍 Buscar y Filtrar")
col1, col2, col3, col4 = st.columns(4)

with col1:
    search_text = st.text_input("🔎 Buscar:", placeholder="Blanco, Azul, etc")

with col2:
    marca_filter = st.selectbox(
        "Marca:",
        options=["Todas", "MILAN", "INFINITI"]
    )

with col3:
    tipo_filter = st.selectbox(
        "Tipo:",
        options=["Todas", "Acrílica Superior", "Semigloss", "Satinada", "Epoxi"]
    )

with col4:
    sort_by = st.selectbox(
        "Ordenar por:",
        options=["Fecha", "Color", "P/G"]
    )

st.markdown("---")

# ===== CONEXIÓN CON SHEETS =====
try:
    with st.spinner("📡 Cargando catálogo desde Google Sheets..."):
        # Leer fórmulas activas
        df = listar_formulas(
            marca=None if marca_filter == "Todas" else marca_filter,
            tipo=None if tipo_filter == "Todas" else tipo_filter,
            estatus="ACTIVA"
        )
    
    if df.empty:
        st.warning("📭 No hay fórmulas registradas en el catálogo")
        st.stop()
    
    # Convertir tipos numéricos
    df["PG_Pintura"] = pd.to_numeric(df["PG_Pintura"], errors='coerce')
    df["Total_Ingredientes"] = pd.to_numeric(df["Total_Ingredientes"], errors='coerce')
    
    # Aplicar búsqueda por texto (en color)
    if search_text:
        df = df[df["Color"].str.contains(search_text, case=False, na=False)]
    
    # Ordenar
    if sort_by == "Fecha":
        df = df.sort_values("Fecha_Creacion", ascending=False)
    elif sort_by == "Color":
        df = df.sort_values("Color")
    elif sort_by == "P/G":
        df = df.sort_values("PG_Pintura", ascending=False)
    
except Exception as e:
    st.error(f"❌ Error conectando con Google Sheets: {e}")
    st.stop()

# ===== TABLA PRINCIPAL =====
st.markdown(f"### 📋 Resultados ({len(df)} fórmulas)")

if not df.empty:
    # Seleccionar columnas para mostrar
    display_cols = ["Formula_Key", "Tipo", "Color", "PG_Pintura", "Total_Ingredientes"]
    display_df = df[display_cols].copy()
    display_df.columns = ["Formula Key", "Tipo", "Color", "P/G", "Ingredientes"]
    
    # Formatear P/G
    display_df["P/G"] = display_df["P/G"].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "N/A")
    
    st.dataframe(
        display_df,
        use_container_width=True,
        height=350,
        hide_index=True
    )
    
    st.markdown("---")
    
    # ===== DETALLES EXPANDIBLES =====
    st.markdown("### 👁️ Detalles de Fórmulas")
    
    for idx, row in df.iterrows():
        formula_key = row["Formula_Key"]
        
        with st.expander(f"🔍 {formula_key} - {row['Color']}"):
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("Marca", row["Marca"])
            with col2:
                st.metric("Tipo", row["Tipo"])
            with col3:
                st.metric("P/G", f"{row['PG_Pintura']:.2f}" if pd.notna(row['PG_Pintura']) else "N/A")
            with col4:
                st.metric("Vol. Base", f"{row['Volumen_Base']} gal")
            
            # Mostrar ingredientes desde Formulas_Detalle
            st.markdown("#### 🧪 Ingredientes")
            
            try:
                df_ing = obtener_ingredientes_formula(formula_key)
                
                if not df_ing.empty:
                    # Seleccionar columnas relevantes
                    cols_display = ["Linea", "Codigo", "Nombre", "Cantidad", "Unidad", "Etapa"]
                    df_ing_display = df_ing[cols_display].copy()
                    
                    st.dataframe(
                        df_ing_display,
                        use_container_width=True,
                        hide_index=True,
                        height=250
                    )
                else:
                    st.info("📭 No se encontraron ingredientes para esta fórmula")
                    
            except Exception as e:
                st.error(f"❌ Error cargando ingredientes: {e}")
            
            # Botón generar orden
            col_btn1, col_btn2, col_btn3 = st.columns(3)
            with col_btn1:
                if st.button(
                    "🏭 Generar Orden",
                    key=f"btn_orden_{formula_key}",
                    use_container_width=True
                ):
                    st.session_state["selected_formula"] = formula_key
                    st.switch_page("pages/generar_orden.py")
            with col_btn2:
                if st.button(
                    "✏️ Actualizar",
                    key=f"btn_editar_{formula_key}",
                    use_container_width=True
                ):
                    st.switch_page("pages/nueva_formula.py")
            with col_btn3:
                if st.button(
                    "📄 Ver PDF",
                    key=f"btn_pdf_{formula_key}",
                    use_container_width=True,
                    disabled=True  # Habilitaremos en Fase 2
                ):
                    st.info("Función PDF próximamente")

            st.markdown("---")
            with st.expander("Zona de eliminación"):
                st.warning(
                    "Esta acción borra solo el Formula_Key exacto en "
                    "GREQ_Formulas y Formulas_Detalle. No toca órdenes ni historial."
                )

                try:
                    impacto = obtener_impacto_eliminacion_formula(formula_key)
                except Exception as e:
                    st.error(f"No se pudo calcular el impacto: {e}")
                    impacto = None

                if impacto:
                    col_i1, col_i2 = st.columns(2)
                    with col_i1:
                        st.metric("Filas en GREQ_Formulas", len(impacto["formula_rows"]))
                    with col_i2:
                        st.metric("Filas en Formulas_Detalle", len(impacto["detalle_rows"]))

                    if not impacto["can_delete"]:
                        st.error(impacto["reason"])
                    else:
                        confirm_key = st.text_input(
                            "Para borrar, escribe el Formula_Key exacto:",
                            key=f"delete_confirm_{formula_key}",
                            placeholder=formula_key,
                        )
                        understand = st.checkbox(
                            "Entiendo que esta acción borra la fórmula del catálogo.",
                            key=f"delete_ack_{formula_key}",
                        )
                        can_submit = confirm_key.strip() == formula_key and understand
                        if st.button(
                            "Borrar fórmula",
                            key=f"btn_delete_{formula_key}",
                            type="secondary",
                            disabled=not can_submit,
                            use_container_width=True,
                        ):
                            success, message, delete_impact = eliminar_formula(
                                formula_key,
                                confirm_key,
                            )
                            if success:
                                st.success(
                                    f"{message} Se borró 1 fila de GREQ_Formulas y "
                                    f"{len(delete_impact['detalle_rows'])} filas de Formulas_Detalle."
                                )
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error(message)
            
else:
    st.info("📭 No hay fórmulas que coincidan con los filtros")

st.markdown("---")

# ===== ESTADÍSTICAS GLOBALES =====
st.markdown("### 📊 Estadísticas del Catálogo")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("Total Fórmulas", len(df))
with col2:
    st.metric("Marcas", df["Marca"].nunique() if not df.empty else 0)
with col3:
    st.metric("Tipos", df["Tipo"].nunique() if not df.empty else 0)
with col4:
    avg_pg = df["PG_Pintura"].mean() if not df.empty and df["PG_Pintura"].notna().any() else 0
    st.metric("P/G Promedio", f"{avg_pg:.2f}")
