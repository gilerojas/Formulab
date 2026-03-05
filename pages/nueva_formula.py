"""
Crear nueva fórmula - Parser + Validación v2.0
Con dropdown de tipos para evitar "GEN"
"""
import streamlit as st
import pandas as pd 
from utils.styling import render_header, apply_custom_css, COLORS
from components.validators import DisplayValidation, ValidationResult
from components.cards import AlertCard
from formulab.formulab_api import procesar_formula

# Importar managers
from formulab.sheets.formulas_manager import guardar_formula, buscar_formula, actualizar_formula, obtener_ingredientes_formula
from formulab.sheets.tipo_mapeo_manager import obtener_lista_tipos, get_tipo_tag_directo


def _build_diff_table(df_old, df_new_escalado):
    """
    Compares old ingredients (from Formulas_Detalle) vs new (from df_escalado).
    Returns a display DataFrame with an 'Estado' column.
    """
    old_map = {}
    for _, row in df_old.iterrows():
        key = str(row.get("Nombre", "")).strip().upper()
        if key:
            old_map[key] = {
                "display": str(row.get("Nombre", "")),
                "cant": float(row.get("Cantidad", 0)) if pd.notna(row.get("Cantidad")) else 0.0,
            }

    new_map = {}
    for _, row in df_new_escalado.iterrows():
        key = str(row.get("nombre", "")).strip().upper()
        if key:
            new_map[key] = {
                "display": str(row.get("nombre", "")),
                "cant": float(row.get("CANT", 0)) if pd.notna(row.get("CANT")) else 0.0,
            }

    # Preserve new order first, then append old-only keys
    seen = set()
    ordered_keys = []
    for key in list(new_map.keys()) + list(old_map.keys()):
        if key not in seen:
            seen.add(key)
            ordered_keys.append(key)

    rows = []
    for key in ordered_keys:
        in_old = key in old_map
        in_new = key in new_map

        if in_old and in_new:
            old_cant = old_map[key]["cant"]
            new_cant = new_map[key]["cant"]
            diff = new_cant - old_cant
            if abs(diff) < 1e-6:
                estado = "Sin cambio"
                delta_str = "—"
            else:
                estado = "Modificado"
                sign = "+" if diff > 0 else ""
                delta_str = f"{sign}{diff:.2f}"
            rows.append({
                "Ingrediente": new_map[key]["display"],
                "CANT Anterior": f"{old_cant:.2f}",
                "CANT Nueva": f"{new_cant:.2f}",
                "Delta": delta_str,
                "Estado": estado,
            })
        elif in_old:
            rows.append({
                "Ingrediente": old_map[key]["display"],
                "CANT Anterior": f"{old_map[key]['cant']:.2f}",
                "CANT Nueva": "—",
                "Delta": "—",
                "Estado": "Removido",
            })
        else:
            rows.append({
                "Ingrediente": new_map[key]["display"],
                "CANT Anterior": "—",
                "CANT Nueva": f"{new_map[key]['cant']:.2f}",
                "Delta": "—",
                "Estado": "Nuevo",
            })

    return pd.DataFrame(rows)


def _style_diff(df):
    def color_row(row):
        estado = row["Estado"]
        if estado == "Removido":
            return ["background-color: #ffcccc"] * len(row)
        elif estado == "Nuevo":
            return ["background-color: #ccf5cc"] * len(row)
        elif estado == "Modificado":
            return ["background-color: #fff3cd"] * len(row)
        return [""] * len(row)
    return df.style.apply(color_row, axis=1)

apply_custom_css()

render_header(
    title="Nueva Fórmula",
    subtitle="Selecciona tipo y pega el texto de la fórmula para validarla",
    emoji="📝"
)

st.markdown("---")

# ===== SECCIÓN 1: METADATA MANUAL =====
st.markdown("### 1️⃣ Información Base")

col1, col2 = st.columns(2)

with col1:
    marca = st.radio(
        "Marca:",
        options=["INFINITI", "MILAN"],
        horizontal=True,
        key="marca_input",
        help="Marca del producto final"
    )

with col2:
    # 🆕 DROPDOWN DE TIPOS
    tipos_disponibles = obtener_lista_tipos()
    
    tipo_seleccionado = st.selectbox(
        "Tipo de Pintura:",
        options=tipos_disponibles,
        key="tipo_input",
        help="⚠️ Selecciona ANTES de parsear para evitar formula_key 'GEN'"
    )
    
    # Mostrar tag preview
    tipo_tag = get_tipo_tag_directo(tipo_seleccionado)
    
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 6px 12px;
        border-radius: 6px;
        color: white;
        font-weight: 600;
        font-size: 0.85rem;
        text-align: center;
        margin-top: -8px;
    ">
        🏷️ Tag: {tipo_tag}
    </div>
    """, unsafe_allow_html=True)

# Observaciones
observaciones = st.text_input(
    "Observaciones (opcional):",
    placeholder="Ej: Actualización nov 2025",
    key="obs_input"
)

st.markdown("---")

# ===== SECCIÓN 2: FÓRMULA CRUDA =====
st.markdown("### 2️⃣ Texto de Fórmula")

formula_text = st.text_area(
    "Contenido de fórmula (copiar desde Excel/PDF):",
    height=200,
    placeholder="""ACRILICA SUPERIOR HP    VOLUMEN    P/G
BLANCO 100-66           100        5.46

CODIGO  NOMBRE         CANT  UNIDAD  KG/GL
SV-001  AGUA           12.0  KG      3.78
RV-002  RESINA         25.0  KG      4.20
...""",
    key="formula_input"
)

# Debug mode
debug_mode = st.checkbox(
    "🔍 Modo Debug (ver parsing detallado)",
    value=False,
    key="debug_toggle"
)

st.markdown("---")

# ===== BOTÓN VALIDAR =====
if st.button("🔍 Validar Fórmula", use_container_width=True, type="primary", key="btn_validar"):
    if not formula_text.strip():
        st.warning("⚠️ Por favor pega el contenido de la fórmula")
    else:
        with st.spinner("🔄 Validando fórmula..."):
            try:
                # 🆕 PASAR TIPO OVERRIDE AL API
                result = procesar_formula(
                    formula_text,
                    gal_objetivo=100,
                    marca=marca,
                    tipo_override=tipo_seleccionado  # ← CRÍTICO
                )
                
                # Guardar en session state
                st.session_state["validated_result"] = result
                st.session_state["observaciones"] = observaciones
                st.session_state["debug_mode"] = debug_mode
                
                st.success("✅ Fórmula validada. Revisa el preview abajo.")
                st.rerun()
                
            except Exception as e:
                st.error(f"❌ Error al procesar fórmula: {str(e)}")
                import traceback
                
                with st.expander("🔍 Ver error completo"):
                    st.code(traceback.format_exc())

# ===== PREVIEW SI EXISTE RESULTADO =====
if "validated_result" in st.session_state:
    result = st.session_state["validated_result"]
    observaciones_saved = st.session_state.get("observaciones", "")
    show_debug = st.session_state.get("debug_mode", False)
    
    # ===== DEBUG DISPLAY =====
    if show_debug:
        st.markdown("---")
        st.markdown("### 🔍 DEBUG: Resultado del Parser")
        
        with st.expander("📊 Metadata detectado", expanded=True):
            st.json(result["meta"])
        
        with st.expander("📋 DataFrame escalado (primeras 10 filas)", expanded=True):
            st.dataframe(result["df_escalado"].head(10))
        
        with st.expander("🔬 DEBUG GL_PRO - Valores detallados"):
            st.write("**Primeras 10 filas de GL_PRO:**")
            st.write(result["df_escalado"]["GL_PRO"].head(10).tolist())
            
            st.write("**Estadísticas:**")
            st.write(f"- Min: {result['df_escalado']['GL_PRO'].min()}")
            st.write(f"- Max: {result['df_escalado']['GL_PRO'].max()}")
            st.write(f"- NaN count: {result['df_escalado']['GL_PRO'].isna().sum()}")
            
            nan_rows = result["df_escalado"][result["df_escalado"]["GL_PRO"].isna()]
            if len(nan_rows) > 0:
                st.dataframe(nan_rows[["nombre", "CANT", "GL_PRO"]])
                st.error(f"⚠️ {len(nan_rows)} ingrediente(s) con GL_PRO = NaN")
        
        with st.expander("⚠️ Issues detectados"):
            if result["issues"]:
                for issue in result["issues"]:
                    st.warning(issue)
            else:
                st.success("No hay issues")
        
        st.markdown("---")
    
    # Preparar ValidationResult
    validation = ValidationResult(
        is_valid=result["valid"],
        issues=result["issues"] if not result["valid"] else [],
        warnings=result["issues"] if "warnings" in result else [],
        metrics=result.get("metrics", {})
    )
    
    # Mostrar validación
    st.markdown("### ✅ Resultado de Validación")
    DisplayValidation(validation)
    
    # ===== PREVIEW DE FÓRMULA =====
# ===== PREVIEW DE FÓRMULA =====
    if result["valid"]:
        st.markdown("---")
        st.markdown("### 📋 Preview de Fórmula")
        
        # 🆕 FILA 1: Formula Key y Tipo (más espacio)
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**Formula Key:**")
            st.code(result["formula_key"], language=None)  # ← Más legible
        
        with col2:
            st.markdown("**Tipo:**")
            st.info(result["meta"].get("tipo", "—"))  # ← Con color
        
        # 🆕 FILA 2: Ingredientes y P/G
        col3, col4 = st.columns(2)
        
        with col3:
            st.metric(
                label="📦 Ingredientes",
                value=len(result["df_escalado"]),
                delta=None
            )
        
        with col4:
            pg = result["meta"].get("P/G", 0)
            st.metric(
                label="⚖️ P/G",
                value=f"{pg:.2f}",
                delta=None
            )
        
        # Tabla de ingredientes
        st.markdown(f"#### Ingredientes (Base: {result['meta'].get('gal_producir', 100)} gal)")

        df_display = result["df_escalado"].copy()
        cols_to_show = ["Codigo", "nombre", "CANT", "KG_PRO", "GL_PRO"]
        
        available_cols = [col for col in cols_to_show if col in df_display.columns]

        if available_cols:
            display_df = df_display[available_cols].copy()
            
            # Renombrar
            rename_map = {
                "Codigo": "Código",
                "nombre": "Nombre",
                "CANT": "Cantidad (%)",
                "KG_PRO": "KG/Producir",
                "GL_PRO": "GL/Producir"
            }
            display_df = display_df.rename(columns=rename_map)
            
            # Formatear
            for col in display_df.columns:
                if col in ["Cantidad (%)", "KG/Producir"]:
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.2f}" if pd.notna(x) else "—")
                elif col == "GL/Producir":
                    display_df[col] = display_df[col].apply(lambda x: f"{x:.3f}" if pd.notna(x) else "—")
            
            st.dataframe(display_df, use_container_width=True, height=300)
        
        st.markdown("---")

        # ===== VERIFICAR DUPLICADOS =====
        formula_key = result["formula_key"]
        existe = buscar_formula(formula_key)
        existe_real = existe is not None and bool(existe)

        if existe_real:
            st.warning(f"⚠️ La fórmula **{formula_key}** ya existe en el catálogo")

            # ===== DIFF: comparar ingredientes actuales vs nuevos =====
            df_old_ing = obtener_ingredientes_formula(formula_key)
            if not df_old_ing.empty:
                st.markdown("#### Comparativo de cambios")

                df_diff = _build_diff_table(df_old_ing, result["df_escalado"])

                n_modified = int((df_diff["Estado"] == "Modificado").sum())
                n_added    = int((df_diff["Estado"] == "Nuevo").sum())
                n_removed  = int((df_diff["Estado"] == "Removido").sum())
                n_unchanged = int((df_diff["Estado"] == "Sin cambio").sum())

                mc1, mc2, mc3, mc4 = st.columns(4)
                mc1.metric("Modificados", n_modified)
                mc2.metric("Nuevos", n_added)
                mc3.metric("Removidos", n_removed)
                mc4.metric("Sin cambio", n_unchanged)

                st.dataframe(
                    _style_diff(df_diff),
                    use_container_width=True,
                    hide_index=True,
                    column_config={
                        "Estado": st.column_config.TextColumn("Estado", width="small"),
                        "Delta": st.column_config.TextColumn("Δ CANT", width="small"),
                    },
                )
            else:
                st.info("No se pudieron cargar los ingredientes actuales para comparar.")

            st.markdown("---")
            col_ver, col_sobreescribir = st.columns(2)

            with col_ver:
                if st.button("Ver en Catálogo", use_container_width=True, key="btn_ver_catalogo"):
                    st.session_state["selected_formula"] = formula_key
                    st.switch_page("pages/catalogo.py")

            with col_sobreescribir:
                if st.button("Actualizar en catálogo", use_container_width=True, type="primary", key="btn_sobreescribir"):
                    with st.spinner("Actualizando en Google Sheets..."):
                        try:
                            meta = {
                                "Marca": result["meta"].get("marca", "N/A"),
                                "Tipo": result["meta"].get("tipo", "N/A"),
                                "Color": result["meta"].get("color", "N/A"),
                                "Volumen_Base": float(result["meta"].get("gal_producir", 100)),
                                "PG_Pintura": float(result["meta"].get("P/G", 0)),
                                "Estatus": "ACTIVA",
                                "Observaciones": observaciones_saved,
                            }
                            df_ing = result["df_escalado"].copy()
                            if "CODIGO" in df_ing.columns and "Codigo" not in df_ing.columns:
                                df_ing["Codigo"] = df_ing["CODIGO"]
                            if "nombre" in df_ing.columns and "Nombre" not in df_ing.columns:
                                df_ing["Nombre"] = df_ing["nombre"]
                            if "CANT" in df_ing.columns and "Cantidad" not in df_ing.columns:
                                df_ing["Cantidad"] = df_ing["CANT"]
                            df_ing["Formula_Key"] = formula_key
                            df_ing["Linea"] = range(1, len(df_ing) + 1)
                            _, success = actualizar_formula(formula_key, meta, df_ing, observaciones=observaciones_saved)
                            if success:
                                st.success(f"Formula **{formula_key}** actualizada en el catálogo.")
                                for k in ["validated_result", "observaciones", "debug_mode"]:
                                    if k in st.session_state:
                                        del st.session_state[k]
                                st.cache_data.clear()
                                st.rerun()
                            else:
                                st.error("No se pudo actualizar.")
                        except Exception as e:
                            st.error(f"Error: {e}")

        else:
            # ===== BOTÓN GUARDAR =====
            col_spacer, col_btn, col_spacer2 = st.columns([1, 2, 1])
            
            with col_btn:
                if st.button(
                    "💾 Guardar en Catálogo",
                    use_container_width=True,
                    type="primary",
                    key="btn_guardar_formula"
                ):
                    with st.spinner("💾 Guardando en Google Sheets..."):
                        try:
                            saved_key, success = guardar_formula(result, observaciones_saved)
                            
                            if success:
                                st.success(f"✅ **Fórmula guardada:** {saved_key}")
                                st.balloons()
                                
                                # Limpiar session state
                                for key in ["validated_result", "observaciones", "debug_mode"]:
                                    if key in st.session_state:
                                        del st.session_state[key]
                                
                                st.cache_data.clear()
                                
                                # Navegación
                                col_cat, col_orden = st.columns(2)
                                
                                with col_cat:
                                    if st.button("📚 Ver en Catálogo", key="btn_ir_catalogo"):
                                        st.switch_page("pages/catalogo.py")
                                
                                with col_orden:
                                    if st.button("🏭 Generar Orden", key="btn_ir_orden"):
                                        st.session_state["selected_formula"] = saved_key
                                        st.switch_page("pages/generar_orden.py")
                            
                            else:
                                st.error("❌ No se pudo guardar la fórmula")
                        
                        except Exception as e:
                            st.error(f"❌ Error guardando: {e}")
                            import traceback
                            with st.expander("🔍 Ver error completo"):
                                st.code(traceback.format_exc())

st.markdown("---")

# ===== AYUDA =====
with st.expander("📖 ¿Cómo usar?"):
    st.markdown("""
    ### Paso a paso:
    
    1. **Selecciona marca** (INFINITI o MILAN)
    2. **Selecciona tipo de pintura** del dropdown ⚠️ IMPORTANTE
    3. **Copia el texto** de la fórmula desde Excel
    4. **Pégalo** en el área de texto
    5. **Haz clic** en "🔍 Validar Fórmula"
    6. **Revisa** el preview y formula_key generada
    7. **Guarda** cuando esté validado ✅
    
    ### 💡 ¿Por qué seleccionar tipo primero?
    
    Para evitar que el sistema genere formula_key con "GEN" (genérico).
    Al seleccionar el tipo manualmente, garantizas claves únicas y descriptivas.
    
    **Ejemplo:**
    - ❌ Sin selección: `IN-GEN-BLANCO100` (ambiguo)
    - ✅ Con selección: `IN-HP-BLANCO100` (claro)
    """)