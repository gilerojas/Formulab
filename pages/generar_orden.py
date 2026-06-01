"""
Generar orden de producción - Escalado visual
"""

import streamlit as st
import pandas as pd
from utils.styling import render_header, apply_custom_css, COLORS
from components.tables import IngredientsTable, ComparisonTable
from components.cards import MetricCard, StatusCard, AlertCard
from formulab.formulab_api import procesar_formula
from utils.whatsapp_notifier import enviar_notificacion_orden
from formulab.sheets.ordenes_manager import registrar_orden


# Importar managers de Sheets
from formulab.sheets.formulas_manager import (
    listar_formulas,
    obtener_ingredientes_formula,
    buscar_formula,
)

apply_custom_css()

render_header(
    title="Generar Orden de Producción",
    subtitle="Escalado automático de fórmula",
    emoji="🏭",
)

st.markdown("---")


# ===== DEFINICIÓN DE TIPOS =====
TIPOS_FORMULAS = {
    "TODOS": "Todos los tipos",
    "GEN": "Sin tipo asignado",
    "HP": "Acrílica Superior HP",
    "SUP-B": "Acrílica Superior Tipo B",
    "BCL": "Barniz Clear Industrial",
    "BEP": "Barniz Port Epoxi Clear",
    "DRY": "Dry Wet",
    "ECO": "Económica",
    "EPO": "Epoxica",
    "EIN": "Esmalte Industrial",
    "EANT": "Esmalte Anticorrosivo",
    "EMAN": "Esmalte Mantenimiento",
    "ETR": "Esmalte Tráfico",
    "PCA": "Pintura P/ Cancha",
    "PRI": "Primer Acrílico",
    "PRO": "Proyecto Contractor",
    "PTE": "Proyecto P/ Techos",
    "SAT": "Satinada",
    "SEW": "Sealer Water",
    "SPP": "Sellador P/ Pisos",
    "SLP": "Sellador Techos HP",
    "SLT": "Sellador Techos Tipo B",
    "SEM-P": "Semigloss Premium",
    "SEM-B": "Semigloss Tipo B",
    "TXT": "Texturizadas"
}


def extraer_tipo_de_formula_key(formula_key: str) -> str:
    """
    Extrae el código de tipo del Formula_Key.
    Formato esperado: MARCA-TIPO-COLOR
    Ejemplos:
      PM-HP-BLANCO00 -> HP
      IN-SLT-GRIS26 -> SLT
      PM-SEM-P-GRISCLARO26 -> SEM-P
      IN-GEN-TIPOREVETESX -> GEN
    """
    parts = formula_key.split("-")
    
    if len(parts) < 2:
        return "GEN"  # Sin tipo identificable
    
    # El tipo está en la segunda posición
    tipo = parts[1]
    
    # Caso especial: SEM-P y SEM-B (3 partes antes del color)
    if tipo == "SEM" and len(parts) >= 3:
        subtipo = parts[2]
        if subtipo in ["P", "B"]:
            return f"SEM-{subtipo}"
    
    # Caso especial: SUP-B
    if tipo == "SUP" and len(parts) >= 3:
        if parts[2] == "B":
            return "SUP-B"
    
    return tipo


# ===== CARGAR FÓRMULAS REALES DE SHEETS =====
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_formulas(marca=None, tipo=None):
    """
    Carga fórmulas activas desde Google Sheets con filtros opcionales
    
    Args:
        marca: "MILAN", "INFINITI", o None para todas
        tipo: Código de tipo (ej: "HP", "SAT") o "TODOS"/"GEN"
    """
    df = listar_formulas(estatus="ACTIVA")
    
    if df.empty:
        return df
    
    # Filtrar por marca
    if marca and marca != "TODAS":
        marca_norm = str(marca).strip().upper()
        df = df[df["Marca"].fillna("").astype(str).str.strip().str.upper() == marca_norm]
    
    # Extraer tipo de cada Formula_Key
    df = df.copy()
    df["Formula_Key"] = df["Formula_Key"].fillna("").astype(str).str.strip()
    df["Tipo_Extraido"] = df["Formula_Key"].apply(extraer_tipo_de_formula_key)
    
    # Filtrar por tipo
    if tipo and tipo != "TODOS":
        if tipo == "GEN":
            # Fórmulas sin tipo o con GEN
            df = df[df["Tipo_Extraido"] == "GEN"]
        else:
            df = df[df["Tipo_Extraido"] == tipo]
    
    return df


# ===== SELECTOR DE MARCA =====
st.markdown("### 🏷️ Filtros de Búsqueda")

col_marca1, col_marca2, col_marca3 = st.columns([1, 1, 2])

with col_marca1:
    btn_milan = st.button(
        "🎨 MILAN",
        use_container_width=True,
        type="primary" if st.session_state.get("marca_selected") == "MILAN" else "secondary",
        key="btn_milan"
    )

with col_marca2:
    btn_infiniti = st.button(
        "✨ INFINITI",
        use_container_width=True,
        type="primary" if st.session_state.get("marca_selected") == "INFINITI" else "secondary",
        key="btn_infiniti"
    )

# Manejar selección de marca
if btn_milan:
    st.session_state["marca_selected"] = "MILAN"
    # Limpiar fórmula seleccionada anterior
    if "selected_formula" in st.session_state:
        del st.session_state["selected_formula"]
    st.rerun()

if btn_infiniti:
    st.session_state["marca_selected"] = "INFINITI"
    # Limpiar fórmula seleccionada anterior
    if "selected_formula" in st.session_state:
        del st.session_state["selected_formula"]
    st.rerun()

# Verificar que se haya seleccionado marca
if "marca_selected" not in st.session_state:
    st.info("👆 Selecciona una marca para continuar")
    st.stop()

marca_actual = st.session_state["marca_selected"]

# Mostrar marca seleccionada
with col_marca3:
    if marca_actual == "MILAN":
        st.info("📌 **Marca activa:** MILAN")
    else:
        st.success("📌 **Marca activa:** INFINITI")


# ===== SELECTOR DE TIPO =====
st.markdown("#### 🔖 Filtrar por Tipo")

# Inicializar tipo si no existe
if "tipo_selected" not in st.session_state:
    st.session_state["tipo_selected"] = "TODOS"

# Crear opciones para selectbox
tipo_options = list(TIPOS_FORMULAS.keys())
tipo_labels = [f"{k} - {v}" for k, v in TIPOS_FORMULAS.items()]

# Encontrar índice del tipo actual
try:
    current_idx = tipo_options.index(st.session_state["tipo_selected"])
except ValueError:
    current_idx = 0

col_tipo1, col_tipo2 = st.columns([2, 1])

with col_tipo1:
    tipo_selected = st.selectbox(
        "Selecciona tipo de fórmula:",
        options=tipo_options,
        format_func=lambda x: TIPOS_FORMULAS[x],
        index=current_idx,
        key="tipo_selectbox"
    )

with col_tipo2:
    # Botón para resetear filtro de tipo
    if st.button("🔄 Ver Todos", use_container_width=True, key="btn_reset_tipo"):
        st.session_state["tipo_selected"] = "TODOS"
        if "selected_formula" in st.session_state:
            del st.session_state["selected_formula"]
        st.rerun()

# Actualizar session state si cambió
if tipo_selected != st.session_state["tipo_selected"]:
    st.session_state["tipo_selected"] = tipo_selected
    if "selected_formula" in st.session_state:
        del st.session_state["selected_formula"]
    st.rerun()

tipo_actual = st.session_state["tipo_selected"]

# Mostrar filtro activo
if tipo_actual != "TODOS":
    st.caption(f"🎯 Filtro activo: **{TIPOS_FORMULAS[tipo_actual]}**")

st.markdown("---")


# ===== CARGAR FÓRMULAS FILTRADAS =====
if st.button("🔄 Refrescar catálogo desde Sheets", use_container_width=True, key="btn_refresh_formulas"):
    st.cache_data.clear()
    st.rerun()

with st.spinner(f"📡 Cargando fórmulas de {marca_actual}..."):
    df_formulas = load_formulas(marca=marca_actual, tipo=tipo_actual)

if df_formulas.empty:
    st.warning(f"⚠️ No hay fórmulas de **{marca_actual}** con tipo **{TIPOS_FORMULAS[tipo_actual]}**.")
    
    # Botón para cambiar filtros
    col_btn1, col_btn2 = st.columns(2)
    
    with col_btn1:
        if st.button("🔄 Cambiar marca", key="btn_cambiar_marca"):
            del st.session_state["marca_selected"]
            st.rerun()
    
    with col_btn2:
        if st.button("🔄 Ver todos los tipos", key="btn_ver_todos"):
            st.session_state["tipo_selected"] = "TODOS"
            st.rerun()
    
    st.stop()

# Mostrar contador de fórmulas
st.info(f"📊 **{len(df_formulas)} fórmulas** encontradas ({marca_actual} - {TIPOS_FORMULAS[tipo_actual]})")

# ===== PASO 1: SELECCIONAR FÓRMULA =====
st.markdown("### 1️⃣ Seleccionar Fórmula")

# Crear opciones para el selectbox
formula_options = df_formulas["Formula_Key"].tolist()

# Si viene de catalogo con fórmula pre-seleccionada
default_idx = 0
if "selected_formula" in st.session_state:
    try:
        default_idx = formula_options.index(st.session_state["selected_formula"])
    except ValueError:
        pass

selected_formula_key = st.selectbox(
    "Fórmula:", options=formula_options, index=default_idx, key="formula_select"
)

# Obtener metadata de la fórmula seleccionada
formula_info = buscar_formula(selected_formula_key)

if not formula_info:
    st.error(f"❌ No se pudo cargar la fórmula {selected_formula_key}")
    st.stop()

# Mostrar información de fórmula base
st.markdown("#### 📋 Información de la Fórmula")

with st.container(border=True):
    col1, col2 = st.columns(2)

    with col1:
        st.markdown(f"**Marca:** {formula_info.get('Marca', 'N/A')}")
        st.markdown(f"**Tipo:** {formula_info.get('Tipo', 'N/A')}")

    with col2:
        st.markdown(f"**Color:** {formula_info.get('Color', 'N/A')}")
        pg_base = float(formula_info.get("PG_Pintura", 0))
        st.markdown(f"**P/G Base:** {pg_base:.2f} kg/gal")

st.markdown("---")

# ===== PASO 2: GALONES A PRODUCIR =====
st.markdown("### 2️⃣ Galones a Producir")

# Inicializar valor en session_state si no existe
if "gal_objetivo" not in st.session_state:
    st.session_state["gal_objetivo"] = 25.0

col1, col2 = st.columns([3, 1])

with col1:
    galones_slider = st.slider(
        "Desliza para seleccionar galones:",
        min_value=0.20,
        max_value=500.0,
        value=st.session_state["gal_objetivo"],
        step=0.25,
        key="gal_slider",
        on_change=lambda: st.session_state.update(
            {"gal_objetivo": st.session_state["gal_slider"]}
        ),
    )

with col2:
    galones_input = st.number_input(
        "O escribe:",
        min_value=0.20,
        max_value=500.0,
        value=st.session_state["gal_objetivo"],
        step=0.25,
        key="gal_input",
        on_change=lambda: st.session_state.update(
            {"gal_objetivo": st.session_state["gal_input"]}
        ),
    )

# Usar el valor sincronizado
galones_objetivo = st.session_state["gal_objetivo"]

st.markdown("---")

# ===== PASO 3: ESCALADO REAL CON FORMULAB =====
st.markdown("### 3️⃣ Preview de Escalado")

# Obtener ingredientes de la fórmula
with st.spinner("🔄 Escalando fórmula..."):
    df_ingredientes = obtener_ingredientes_formula(selected_formula_key)

    if df_ingredientes.empty:
        st.error("❌ No se encontraron ingredientes para esta fórmula")
        st.stop()

    # Reconstruir texto para procesar_formula (formato mínimo)
    # Usar metadata + ingredientes para escalado
    vol_base = float(formula_info.get("Volumen_Base", 100))

    # Crear DataFrame para calcular_escalado directamente
    from formulab.core.engine.escalado_core import calcular_escalado

    # Preparar DataFrame de ingredientes
    df_ingredientes_prep = df_ingredientes.rename(
        columns={
            "Nombre": "nombre",
            "Densidad_KG_GL": "Densidad_KG_GL",
            "Cantidad": "CANT",
        }
    )

    # Calcular escalado
    df_escalado = calcular_escalado(
        ingredientes_df=df_ingredientes_prep,
        gal_objetivo=galones_objetivo,
        pg_pintura=pg_base,
    )

# Mostrar factor de escala
factor = galones_objetivo / vol_base
st.info(f"📊 Factor de escala: **{factor:.2f}x** ({vol_base} → {galones_objetivo} gal)")

# Métricas de escalado
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("Cantidad Base", f"{vol_base} gal")

with col2:
    st.metric("Factor", f"{factor:.2%}")

with col3:
    st.metric("A Producir", f"{galones_objetivo} gal")

# ===== TABLA DE INGREDIENTES ESCALADOS =====
st.markdown("#### Ingredientes a Producir:")

# Agregar columnas faltantes desde df_ingredientes
if "CODIGO" not in df_escalado.columns:
    # Copiar desde df_ingredientes (mismo orden de filas)
    if "CODIGO" in df_ingredientes.columns:
        df_escalado["CODIGO"] = df_ingredientes["CODIGO"].values
    elif "Codigo" in df_ingredientes.columns:
        df_escalado["CODIGO"] = df_ingredientes["Codigo"].values
    else:
        df_escalado["CODIGO"] = ""

if "etapa" not in df_escalado.columns:
    if "Etapa" in df_ingredientes.columns:
        df_escalado["etapa"] = df_ingredientes["Etapa"].values
    elif "etapa" in df_ingredientes.columns:
        df_escalado["etapa"] = df_ingredientes["etapa"].values
    else:
        df_escalado["etapa"] = "Preparación base"

# Construir columnas para display (verificar existencia)
cols_display = []
if "CODIGO" in df_escalado.columns:
    cols_display.append("CODIGO")
if "etapa" in df_escalado.columns:
    cols_display.append("etapa")

# Columnas obligatorias
cols_display.extend(["nombre", "CANT", "KG_PRO", "GL_PRO"])

# Filtrar solo columnas que existen
cols_display = [c for c in cols_display if c in df_escalado.columns]

df_display = df_escalado[cols_display].copy()

# Renombrar columnas para display
rename_map = {
    "CODIGO": "Código",
    "etapa": "Etapa",
    "nombre": "Nombre Genérico",
    "CANT": "CANT (%)",
    "KG_PRO": "KG/PRO",
    "GL_PRO": "GL/PRO",
}

df_display = df_display.rename(columns=rename_map)

# Formatear números
df_display["CANT (%)"] = df_display["CANT (%)"].apply(lambda x: f"{x:.3f}")
df_display["KG/PRO"] = df_display["KG/PRO"].apply(lambda x: f"{x:.2f}")
df_display["GL/PRO"] = df_display["GL/PRO"].apply(lambda x: f"{x:.2f}")

st.dataframe(df_display, use_container_width=True, height=500)

# Totales
st.markdown("#### 📊 Totales")
col1, col2, col3 = st.columns(3)

with col1:
    total_cant = df_escalado["CANT"].sum()
    st.metric("Total CANT", f"{total_cant:.2f}%")

with col2:
    total_kg = df_escalado["KG_PRO"].sum()
    st.metric("Total KG/PRO", f"{total_kg:.2f} kg")

with col3:
    total_gl = df_escalado["GL_PRO"].sum()
    st.metric("Total GL/PRO", f"{total_gl:.2f} gal")

st.markdown("---")

# ===== PASO 4: REFERENCIAS OPCIONALES =====
st.markdown("### 4️⃣ Referencias Opcionales")

col1, col2 = st.columns(2)

with col1:
    ped_id = st.text_input(
        "PED_ID (opcional):", placeholder="PED-2025-150", key="ped_id"
    )

with col2:
    batch_id = st.text_input(
        "Batch ID (opcional):", placeholder="PM-SEM-78-02", key="batch_id"
    )

observaciones = st.text_area(
    "Observaciones (opcional):",
    placeholder="Notas especiales para producción...",
    key="obs_orden",
)

st.markdown("---")

# ===== BOTONES DE ACCIÓN =====
st.markdown("---")

col1, col2 = st.columns([2, 1])

with col1:
    if st.button(
        "🚀 Generar Orden Completa",
        use_container_width=True,
        type="primary",
        key="btn_generar",
    ):
        with st.spinner("🔄 Generando orden..."):
            try:
                from utils.pdf_generator import generar_pdf_orden
                from datetime import datetime

                # 1. Generar Orden ID único
                orden_id = f"ORD-{datetime.now().strftime('%Y-%m-%d-%H%M%S')}"

                # 2. Generar PDF (guardar en ORDENES/ si existe la carpeta)
                import os
                ordenes_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "ORDENES")
                os.makedirs(ordenes_dir, exist_ok=True)
                output_pdf = os.path.join(ordenes_dir, f"{orden_id}.pdf")
                with st.spinner("📄 Generando PDF..."):
                    pdf_path = generar_pdf_orden(
                        orden_id=orden_id,
                        formula_info=formula_info,
                        df_escalado=df_escalado,
                        galones_objetivo=galones_objetivo,
                        ped_id=ped_id,
                        batch_id=batch_id,
                        observaciones=observaciones,
                        output_path=output_pdf,
                    )

                # 3. Guardar en Sheets
                with st.spinner("💾 Guardando en Sheets..."):
                    try:
                        orden_data = {
                            "orden_id": orden_id,
                            "formula_key": selected_formula_key,
                            "gal_objetivo": galones_objetivo,
                            "fecha_generacion": datetime.now().strftime(
                                "%Y-%m-%d %H:%M:%S"
                            ),
                            "ped_id": ped_id or "",
                            "batch_id": batch_id or "",
                            "observaciones": observaciones or "",
                        }
                        registrar_orden(orden_data)
                        sheets_success = True
                    except Exception as e_sheets:
                        print(f"❌ Error guardando en Sheets: {e_sheets}")
                        sheets_success = False

                # 4. Enviar WhatsApp
                with st.spinner("📲 Enviando notificación..."):
                    wa_success = enviar_notificacion_orden(
                        orden_id=orden_id,
                        formula_info=formula_info,
                        galones=galones_objetivo,
                        ped_id=ped_id,
                        batch_id=batch_id,
                    )

                # 5. Leer PDF para descarga
                with open(pdf_path, "rb") as f:
                    pdf_bytes = f.read()

                # ✅ Mostrar resultados
                st.success(f"✅ Orden generada: **{orden_id}**")

                # Status detallado
                col_status1, col_status2, col_status3 = st.columns(3)

                with col_status1:
                    if sheets_success:
                        st.success("💾 Guardado en Sheets")
                    else:
                        st.error("❌ Fallo guardado")

                with col_status2:
                    if wa_success:
                        st.success("📲 WhatsApp enviado")
                    else:
                        st.warning("⚠️ WhatsApp falló")

                with col_status3:
                    st.success("📄 PDF generado")

                # Botón de descarga
                st.download_button(
                    label="⬇️ Descargar PDF",
                    data=pdf_bytes,
                    file_name=f"{orden_id}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                    type="primary",
                )

            except Exception as e:
                st.error(f"❌ Error generando orden: {e}")
                import traceback

                with st.expander("🔍 Ver error completo"):
                    st.code(traceback.format_exc())

with col2:
    if st.button("🔄 Reset Completo", use_container_width=True, key="btn_reset"):
        if "selected_formula" in st.session_state:
            del st.session_state["selected_formula"]
        if "marca_selected" in st.session_state:
            del st.session_state["marca_selected"]
        if "tipo_selected" in st.session_state:
            del st.session_state["tipo_selected"]
        st.rerun()
