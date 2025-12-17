"""
Dashboard principal - Métricas y accesos rápidos
Versión 2.1 - Simplificado y enfocado
"""
import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from utils.styling import render_header, COLORS, apply_custom_css
import plotly.graph_objects as go

# Importar managers de Sheets
from formulab.sheets.formulas_manager import listar_formulas
from formulab.sheets.sheets_connector import read_sheet

apply_custom_css()

render_header(
    title="Dashboard Formulab",
    subtitle="Resumen de producción y fórmulas",
    emoji="📊"
)

st.markdown("---")

# ===== CARGAR DATOS =====
@st.cache_data(ttl=300)
def load_dashboard_data():
    """Carga datos desde Sheets"""
    try:
        # Fórmulas activas
        df_formulas = listar_formulas(estatus="ACTIVA")
        
        # Órdenes
        ordenes_data = read_sheet("Ordenes_Produccion")
        
        if len(ordenes_data) > 1:
            df_ordenes = pd.DataFrame(ordenes_data[1:], columns=[
                "Orden_ID", "Formula_Key", "Gal_Objetivo", "Fecha_Generacion",
                "PED_ID", "Batch_ID", "Observaciones"
            ])
            
            df_ordenes["Gal_Objetivo"] = pd.to_numeric(df_ordenes["Gal_Objetivo"], errors='coerce')
            df_ordenes["Fecha_Generacion"] = pd.to_datetime(df_ordenes["Fecha_Generacion"], errors='coerce')
            df_ordenes = df_ordenes[df_ordenes["Fecha_Generacion"].notna()]
        else:
            df_ordenes = pd.DataFrame(columns=[
                "Orden_ID", "Formula_Key", "Gal_Objetivo", "Fecha_Generacion",
                "PED_ID", "Batch_ID", "Observaciones"
            ])
        
        # Métricas
        total_ordenes = len(df_ordenes)
        volumen_total = df_ordenes["Gal_Objetivo"].sum() if not df_ordenes.empty else 0
        promedio_galones = df_ordenes["Gal_Objetivo"].mean() if not df_ordenes.empty else 0
        
        # Fórmula más usada
        if not df_ordenes.empty:
            formula_top = df_ordenes["Formula_Key"].value_counts().head(1)
            formula_mas_usada = formula_top.index[0] if not formula_top.empty else "N/A"
            uso_formula_top = formula_top.values[0] if not formula_top.empty else 0
        else:
            formula_mas_usada = "N/A"
            uso_formula_top = 0
        
        # Órdenes hoy
        if not df_ordenes.empty:
            hoy = datetime.now().date()
            ordenes_hoy = len(df_ordenes[df_ordenes["Fecha_Generacion"].dt.date == hoy])
        else:
            ordenes_hoy = 0
        
        return {
            "formulas": df_formulas,
            "ordenes": df_ordenes,
            "total_ordenes": total_ordenes,
            "volumen_total": volumen_total,
            "promedio_galones": promedio_galones,
            "ordenes_hoy": ordenes_hoy,
            "formula_mas_usada": formula_mas_usada,
            "uso_formula_top": uso_formula_top
        }
    except Exception as e:
        st.error(f"❌ Error cargando datos: {e}")
        return None

# Cargar datos
with st.spinner("📡 Cargando dashboard..."):
    data = load_dashboard_data()

if not data:
    st.error("❌ No se pudo conectar con Google Sheets")
    st.stop()

# ===== KPIs PRINCIPALES =====
st.markdown("### 📊 Métricas Principales")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="🏭 Órdenes Generadas",
        value=data["total_ordenes"],
        delta=f"+{data['ordenes_hoy']} hoy" if data['ordenes_hoy'] > 0 else None
    )

with col2:
    st.metric(
        label="📦 Volumen Total",
        value=f"{data['volumen_total']:.0f} gal"
    )

with col3:
    st.metric(
        label="📈 Promedio por Orden",
        value=f"{data['promedio_galones']:.1f} gal"
    )

with col4:
    st.metric(
        label="🏆 Fórmula Top",
        value=f"{data['uso_formula_top']}x",
        help=data['formula_mas_usada']
    )

st.markdown("---")

# ===== GRÁFICO: DISTRIBUCIÓN POR TIPO =====
st.markdown("### 📊 Distribución de Fórmulas por Tipo")

if not data["formulas"].empty and "Tipo" in data["formulas"].columns:
    tipos_count = data["formulas"]["Tipo"].value_counts().to_dict()
    
    fig = go.Figure(data=[
        go.Bar(
            x=list(tipos_count.keys()), 
            y=list(tipos_count.values()),
            marker_color=COLORS['primary'],
            text=list(tipos_count.values()),
            textposition='auto'
        )
    ])
    fig.update_layout(
        xaxis_title="Tipo de Producto",
        yaxis_title="Cantidad de Fórmulas",
        height=350,
        showlegend=False
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    st.info("📭 No hay fórmulas registradas")

st.markdown("---")

# ===== TOP 5 FÓRMULAS MÁS USADAS =====
st.markdown("### 🏆 Top 5 Fórmulas Más Solicitadas")

if not data["ordenes"].empty:
    top_formulas = data["ordenes"]["Formula_Key"].value_counts().head(5).reset_index()
    top_formulas.columns = ["Formula_Key", "Cantidad"]
    
    # Calcular volumen por fórmula
    vol_por_formula = data["ordenes"].groupby("Formula_Key")["Gal_Objetivo"].sum()
    top_formulas["Volumen_Total"] = top_formulas["Formula_Key"].map(vol_por_formula)
    
    for idx, row in top_formulas.iterrows():
        col1, col2, col3, col4 = st.columns([3, 1, 1, 1])
        
        with col1:
            st.markdown(f"**{idx+1}. {row['Formula_Key']}**")
        
        with col2:
            st.metric("Órdenes", row['Cantidad'])
        
        with col3:
            st.metric("Volumen", f"{row['Volumen_Total']:.0f} gal")
        
        with col4:
            porcentaje = (row['Cantidad'] / len(data['ordenes']) * 100)
            st.metric("% Total", f"{porcentaje:.1f}%")
else:
    st.info("📭 No hay órdenes registradas")

st.markdown("---")

# ===== ÚLTIMAS 3 ÓRDENES =====
st.markdown("### ⏱️ Últimas Órdenes Generadas")

if not data["ordenes"].empty:
    df_ultimas = data["ordenes"].sort_values("Fecha_Generacion", ascending=False).head(3)
    
    for idx, row in df_ultimas.iterrows():
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
            
            with col1:
                fecha = pd.to_datetime(row["Fecha_Generacion"])
                delta = datetime.now() - fecha
                
                if delta.days > 0:
                    tiempo = f"Hace {delta.days} día(s)"
                elif delta.seconds // 3600 > 0:
                    tiempo = f"Hace {delta.seconds // 3600}h"
                else:
                    tiempo = f"Hace {delta.seconds // 60}m"
                
                st.caption(f"🕐 {tiempo}")
                st.caption(fecha.strftime("%Y-%m-%d %H:%M"))
            
            with col2:
                st.markdown(f"**{row['Orden_ID']}**")
                st.caption(row['Formula_Key'])
            
            with col3:
                st.metric("Volumen", f"{row['Gal_Objetivo']:.0f} gal")
            
            with col4:
                refs = []
                if row['PED_ID']:
                    refs.append(f"📦 {row['PED_ID']}")
                if row['Batch_ID']:
                    refs.append(f"🏷️ {row['Batch_ID']}")
                
                if refs:
                    st.caption("\n".join(refs))
                else:
                    st.caption("—")
else:
    st.info("📭 No hay órdenes registradas")

st.markdown("---")

# ===== ACCESOS RÁPIDOS =====
st.markdown("### 🎯 Accesos Rápidos")
col1, col2, col3, col4 = st.columns(4)

with col1:
    if st.button("📝 Nueva Fórmula", use_container_width=True, key="btn_nueva"):
        st.switch_page("pages/nueva_formula.py")

with col2:
    if st.button("🏭 Generar Orden", use_container_width=True, key="btn_orden"):
        st.switch_page("pages/generar_orden.py")

with col3:
    if st.button("📚 Ver Catálogo", use_container_width=True, key="btn_catalogo"):
        st.switch_page("pages/catalogo.py")

with col4:
    if st.button("🔄 Actualizar", use_container_width=True, key="btn_refresh"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# ===== ESTADO DEL SISTEMA =====
st.markdown("### 🔧 Estado del Sistema")
col1, col2, col3 = st.columns(3)

with col1:
    st.success("✅ API Formulab")

with col2:
    try:
        from formulab.sheets.sheets_connector import get_sheets_client
        get_sheets_client()
        st.success("✅ Google Sheets")
    except:
        st.error("❌ Google Sheets")

with col3:
    st.info(f"ℹ️ {datetime.now().strftime('%H:%M:%S')}")

st.markdown("---")
st.caption(f"📊 {data['total_ordenes']} órdenes | {data['volumen_total']:.0f} galones producidos")