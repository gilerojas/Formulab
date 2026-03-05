"""
Editar Fórmula - Modificar fórmulas existentes en el catálogo
Permite actualizar metadata e ingredientes y sincronizar con Google Sheets.
"""
import streamlit as st
import pandas as pd
from utils.styling import render_header, apply_custom_css
from formulab.sheets.formulas_manager import (
    listar_formulas,
    buscar_formula,
    obtener_ingredientes_formula,
    actualizar_formula,
)
from formulab.sheets.tipo_mapeo_manager import obtener_lista_tipos

apply_custom_css()

render_header(
    title="Editar Fórmula",
    subtitle="Modifica metadata e ingredientes y guarda los cambios en el catálogo",
    emoji="✏️",
)

st.markdown("---")

# ===== CARGAR FÓRMULAS =====
@st.cache_data(ttl=120)
def _load_formulas_list():
    return listar_formulas(estatus=None)

try:
    df_list = _load_formulas_list()
except Exception as e:
    st.error(f"❌ Error cargando catálogo: {e}")
    st.stop()

if df_list.empty:
    st.warning("📭 No hay fórmulas en el catálogo. Crea una desde **Nueva Fórmula**.")
    st.stop()

formula_options = df_list["Formula_Key"].tolist()

# Selector de fórmula (persistir en session_state para no perder al editar)
if "editar_formula_key" not in st.session_state:
    st.session_state["editar_formula_key"] = formula_options[0]

idx_default = formula_options.index(st.session_state["editar_formula_key"]) if st.session_state["editar_formula_key"] in formula_options else 0

selected_key = st.selectbox(
    "Selecciona la fórmula a editar:",
    options=formula_options,
    index=idx_default,
    key="select_editar_formula",
)
st.session_state["editar_formula_key"] = selected_key

# ===== CARGAR DETALLE =====
info = buscar_formula(selected_key)
if not info:
    st.error(f"❌ No se encontró la fórmula **{selected_key}**")
    st.stop()

df_ing = obtener_ingredientes_formula(selected_key)
if df_ing.empty:
    st.warning("⚠️ Esta fórmula no tiene ingredientes cargados. Añade filas abajo y guarda.")

st.markdown("---")
st.markdown("### 📋 Metadata")

tipos_disponibles = obtener_lista_tipos()
tipo_actual = info.get("Tipo", "N/A")
if tipo_actual and tipo_actual not in tipos_disponibles:
    tipos_disponibles = [tipo_actual] + [t for t in tipos_disponibles if t != tipo_actual]

col1, col2, col3 = st.columns(3)
with col1:
    marca = st.text_input("Marca", value=str(info.get("Marca", "")), key="edit_marca")
    tipo = st.selectbox("Tipo", options=tipos_disponibles, index=tipos_disponibles.index(tipo_actual) if tipo_actual in tipos_disponibles else 0, key="edit_tipo")
with col2:
    color = st.text_input("Color", value=str(info.get("Color", "")), key="edit_color")
    vol_base = st.number_input("Volumen base (gal)", min_value=1.0, max_value=1000.0, value=float(info.get("Volumen_Base", 100)), step=1.0, key="edit_vol")
with col3:
    pg_pintura = st.number_input("P/G (kg/gal)", min_value=0.0, value=float(info.get("PG_Pintura", 0)), step=0.01, format="%.2f", key="edit_pg")
    estatus = st.selectbox("Estatus", options=["ACTIVA", "INACTIVA", "OBSOLETA"], index=["ACTIVA", "INACTIVA", "OBSOLETA"].index(str(info.get("Estatus", "ACTIVA"))), key="edit_estatus")

observaciones = st.text_area("Observaciones", value=str(info.get("Observaciones", "")), height=80, key="edit_obs")

st.markdown("---")
st.markdown("### 🧪 Ingredientes")

columnas_detalle = ["Formula_Key", "Linea", "Codigo", "Nombre", "Cantidad", "Unidad", "Densidad_KG_GL", "Etapa"]
for c in columnas_detalle:
    if c not in df_ing.columns:
        df_ing[c] = "" if c != "Formula_Key" else selected_key
        if c == "Formula_Key":
            df_ing[c] = selected_key

df_ing = df_ing[columnas_detalle]
df_ing["Linea"] = range(1, len(df_ing) + 1)

edited = st.data_editor(
    df_ing,
    use_container_width=True,
    height=350,
    num_rows="dynamic",
    column_config={
        "Formula_Key": st.column_config.TextColumn("Formula Key", disabled=True),
        "Linea": st.column_config.NumberColumn("Línea", min_value=1, step=1),
        "Codigo": st.column_config.TextColumn("Código"),
        "Nombre": st.column_config.TextColumn("Nombre"),
        "Cantidad": st.column_config.NumberColumn("Cantidad", format="%.2f"),
        "Unidad": st.column_config.TextColumn("Unidad"),
        "Densidad_KG_GL": st.column_config.NumberColumn("Densidad kg/gal", format="%.2f"),
        "Etapa": st.column_config.TextColumn("Etapa"),
    },
    key="editor_ingredientes",
)

if not edited.empty:
    edited["Formula_Key"] = selected_key
    edited["Linea"] = range(1, len(edited) + 1)

st.markdown("---")

if st.button("💾 Guardar cambios en el catálogo", type="primary", use_container_width=True, key="btn_guardar_edicion"):
    if edited.empty:
        st.warning("⚠️ La fórmula debe tener al menos un ingrediente.")
    else:
        meta = {
            "Marca": marca,
            "Tipo": tipo,
            "Color": color,
            "Volumen_Base": vol_base,
            "PG_Pintura": pg_pintura,
            "Estatus": estatus,
            "Observaciones": observaciones,
        }
        with st.spinner("Guardando en Google Sheets..."):
            try:
                _, ok = actualizar_formula(selected_key, meta, edited, observaciones=observaciones)
                if ok:
                    st.success(f"✅ Fórmula **{selected_key}** actualizada correctamente.")
                    st.cache_data.clear()
                else:
                    st.error("❌ No se pudo actualizar la fórmula.")
            except Exception as e:
                st.error(f"❌ Error: {e}")
                import traceback
                with st.expander("Detalle del error"):
                    st.code(traceback.format_exc())

st.markdown("---")
with st.expander("📖 Cómo editar"):
    st.markdown("""
    1. **Elige la fórmula** en el selector.
    2. **Ajusta** Marca, Tipo, Color, Volumen base, P/G y Estatus si hace falta.
    3. **Edita la tabla de ingredientes**: cambia cantidades, añade o borra filas.
    4. Pulsa **Guardar cambios** para escribir en Google Sheets.
    
    Los cambios se reflejan de inmediato en el catálogo y al generar órdenes.
    """)
