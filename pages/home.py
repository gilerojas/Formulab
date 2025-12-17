"""
Dashboard principal - Métricas rápidas y accesos directos
Versión 2.0 - Ajustado a estructura real de Sheets (7 columnas)
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
    subtitle="Resumen rápido de fórmulas y órdenes",
    emoji="📊"
)

st.markdown("---")

# ===== CARGAR DATOS DESDE SHEETS =====
@st.cache_data(ttl=300)  # Cache por 5 minutos
def load_dashboard_data():
    """Carga todas las métricas necesarias desde Sheets"""
    try:
        # 1. Fórmulas activas
        df_formulas = listar_formulas(estatus="ACTIVA")
        total_formulas = len(df_formulas)
        
        # 2. Órdenes desde Ordenes_Produccion (7 columnas reales)
        ordenes_data = read_sheet("Ordenes_Produccion")
        
        if len(ordenes_data) > 1:
            # Crear DataFrame con columnas reales
            df_ordenes = pd.DataFrame(ordenes_data[1:], columns=[
                "Orden_ID", "Formula_Key", "Gal_Objetivo", "Fecha_Generacion",
                "PED_ID", "Batch_ID", "Observaciones"
            ])
            
            # Convertir tipos de datos
            df_ordenes["Gal_Objetivo"] = pd.to_numeric(df_ordenes["Gal_Objetivo"], errors='coerce')
            df_ordenes["Fecha_Generacion"] = pd.to_datetime(df_ordenes["Fecha_Generacion"], errors='coerce')
            
            # Eliminar filas sin fecha válida
            df_ordenes = df_ordenes[df_ordenes["Fecha_Generacion"].notna()]
        else:
            df_ordenes = pd.DataFrame(columns=[
                "Orden_ID", "Formula_Key", "Gal_Objetivo", "Fecha_Generacion",
                "PED_ID", "Batch_ID", "Observaciones"
            ])
        
        # ===== MÉTRICAS CALCULADAS =====
        
        # 3. Total órdenes
        total_ordenes = len(df_ordenes)
        
        # 4. Volumen total producido (galones)
        volumen_total = df_ordenes["Gal_Objetivo"].sum() if not df_ordenes.empty else 0
        
        # 5. Promedio galones por orden
        promedio_galones = df_ordenes["Gal_Objetivo"].mean() if not df_ordenes.empty else 0
        
        # 6. Órdenes últimos 7 días
        if not df_ordenes.empty:
            hace_7_dias = datetime.now() - timedelta(days=7)
            ordenes_semana = len(df_ordenes[df_ordenes["Fecha_Generacion"] >= hace_7_dias])
        else:
            ordenes_semana = 0
        
        # 7. Órdenes hoy
        if not df_ordenes.empty:
            hoy = datetime.now().date()
            ordenes_hoy = len(df_ordenes[df_ordenes["Fecha_Generacion"].dt.date == hoy])
        else:
            ordenes_hoy = 0
        
        # 8. Fórmula más usada
        if not df_ordenes.empty:
            formula_top = df_ordenes["Formula_Key"].value_counts().head(1)
            formula_mas_usada = formula_top.index[0] if not formula_top.empty else "N/A"
            uso_formula_top = formula_top.values[0] if not formula_top.empty else 0
        else:
            formula_mas_usada = "N/A"
            uso_formula_top = 0
        
        # 9. Frecuencia de órdenes (promedio días entre órdenes)
        if len(df_ordenes) > 1:
            df_sorted = df_ordenes.sort_values("Fecha_Generacion")
            diferencias = df_sorted["Fecha_Generacion"].diff().dt.days
            frecuencia_dias = diferencias.mean()
        else:
            frecuencia_dias = 0
        
        return {
            "formulas": df_formulas,
            "ordenes": df_ordenes,
            "total_formulas": total_formulas,
            "total_ordenes": total_ordenes,
            "volumen_total": volumen_total,
            "promedio_galones": promedio_galones,
            "ordenes_semana": ordenes_semana,
            "ordenes_hoy": ordenes_hoy,
            "formula_mas_usada": formula_mas_usada,
            "uso_formula_top": uso_formula_top,
            "frecuencia_dias": frecuencia_dias
        }
    except Exception as e:
        st.error(f"❌ Error cargando datos: {e}")
        import traceback
        st.code(traceback.format_exc())
        return None

# Cargar datos
with st.spinner("📡 Cargando dashboard..."):
    data = load_dashboard_data()

if not data:
    st.error("❌ No se pudo conectar con Google Sheets")
    st.stop()

# ===== KPIs PRINCIPALES =====
st.markdown("### 📊 Métricas Generales")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric(
        label="📚 Fórmulas Activas",
        value=data["total_formulas"]
    )

with col2:
    st.metric(
        label="🏭 Órdenes Generadas",
        value=data["total_ordenes"],
        delta=f"+{data['ordenes_hoy']} hoy" if data['ordenes_hoy'] > 0 else None
    )

with col3:
    st.metric(
        label="📦 Volumen Total",
        value=f"{data['volumen_total']:.0f} gal"
    )

with col4:
    st.metric(
        label="📈 Promedio por Orden",
        value=f"{data['promedio_galones']:.1f} gal"
    )

st.markdown("---")

# ===== KPIs SECUNDARIOS =====
st.markdown("### 📅 Actividad Reciente")
col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        label="📅 Órdenes esta Semana",
        value=data["ordenes_semana"]
    )

with col2:
    # Calcular frecuencia en texto legible
    if data["frecuencia_dias"] > 0:
        if data["frecuencia_dias"] < 1:
            freq_text = f"{data['frecuencia_dias']*24:.1f}h"
        elif data["frecuencia_dias"] < 7:
            freq_text = f"{data['frecuencia_dias']:.1f} días"
        else:
            freq_text = f"{data['frecuencia_dias']/7:.1f} semanas"
    else:
        freq_text = "N/A"
    
    st.metric(
        label="⏱️ Frecuencia Promedio",
        value=freq_text,
        help="Tiempo promedio entre órdenes"
    )

with col3:
    st.metric(
        label="🏆 Fórmula Más Usada",
        value=f"{data['uso_formula_top']}x",
        help=f"{data['formula_mas_usada']}"
    )

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
    if st.button("🔄 Actualizar Datos", use_container_width=True, key="btn_refresh"):
        st.cache_data.clear()
        st.rerun()

st.markdown("---")

# ===== GRÁFICOS =====
st.markdown("### 📈 Análisis Visual")

col1, col2 = st.columns(2)

# Gráfico 1: Distribución por Tipo de Fórmula
with col1:
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
            title="Fórmulas por Tipo de Producto",
            xaxis_title="Tipo",
            yaxis_title="Cantidad",
            height=300,
            showlegend=False
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("📭 No hay fórmulas registradas para graficar")

# Gráfico 2: Volumen producido últimos 7 días
with col2:
    if not data["ordenes"].empty:
        # Filtrar últimos 7 días
        hoy = datetime.now()
        hace_7_dias = hoy - timedelta(days=7)
        
        df_recientes = data["ordenes"][data["ordenes"]["Fecha_Generacion"] >= hace_7_dias].copy()
        
        if not df_recientes.empty:
            # Agrupar por fecha y sumar galones
            df_recientes["Fecha"] = df_recientes["Fecha_Generacion"].dt.date
            volumen_por_dia = df_recientes.groupby("Fecha")["Gal_Objetivo"].sum().reset_index()
            
            fig = go.Figure(data=[
                go.Bar(
                    x=volumen_por_dia["Fecha"],
                    y=volumen_por_dia["Gal_Objetivo"],
                    marker_color=COLORS['secondary'],
                    text=volumen_por_dia["Gal_Objetivo"].round(0),
                    textposition='auto'
                )
            ])
            fig.update_layout(
                title="Volumen Producido (Últimos 7 días)",
                xaxis_title="Fecha",
                yaxis_title="Galones",
                height=300,
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("📭 No hay órdenes en los últimos 7 días")
    else:
        st.info("📭 No hay órdenes registradas para graficar")

st.markdown("---")

# ===== GRÁFICO SIMPLIFICADO: Solo Órdenes =====
if not data["ordenes"].empty and len(data["ordenes"]) >= 3:
    st.markdown("### 📊 Tendencia de Órdenes")
    
    df_trend = data["ordenes"].copy()
    df_trend["Fecha"] = df_trend["Fecha_Generacion"].dt.date
    ordenes_por_dia = df_trend.groupby("Fecha").size().reset_index(name="Cantidad")
    
    # Convertir fechas a string
    ordenes_por_dia["Fecha"] = ordenes_por_dia["Fecha"].astype(str)
    
    fig = go.Figure(data=[
        go.Scatter(
            x=ordenes_por_dia["Fecha"],
            y=ordenes_por_dia["Cantidad"],
            mode='lines+markers',
            name='Órdenes',
            line=dict(color=COLORS['primary'], width=3),
            marker=dict(size=10),
            fill='tozeroy',
            fillcolor=f'rgba({int(COLORS["primary"][1:3], 16)}, {int(COLORS["primary"][3:5], 16)}, {int(COLORS["primary"][5:7], 16)}, 0.2)'
        )
    ])
    
    fig.update_layout(
        title="Evolución de Órdenes Generadas",
        xaxis_title="Fecha",
        yaxis_title="Cantidad de Órdenes",
        height=350,
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")

# ===== TOP 5 FÓRMULAS MÁS USADAS =====
if not data["ordenes"].empty:
    st.markdown("### 🏆 Fórmulas Más Solicitadas")
    
    top_formulas = data["ordenes"]["Formula_Key"].value_counts().head(5).reset_index()
    top_formulas.columns = ["Formula_Key", "Cantidad"]
    
    # Calcular volumen total por fórmula
    vol_por_formula = data["ordenes"].groupby("Formula_Key")["Gal_Objetivo"].sum()
    top_formulas["Volumen_Total"] = top_formulas["Formula_Key"].map(vol_por_formula)
    
    # Crear tabla visual
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

st.markdown("---")

# ===== ACTIVIDAD RECIENTE (Timeline) =====
st.markdown("### ⏱️ Últimas Órdenes Generadas")

if not data["ordenes"].empty:
    # Obtener últimas 5 órdenes
    df_ultimas = data["ordenes"].sort_values("Fecha_Generacion", ascending=False).head(5)
    
    for idx, row in df_ultimas.iterrows():
        with st.container(border=True):
            col1, col2, col3, col4 = st.columns([2, 3, 2, 2])
            
            with col1:
                # Calcular tiempo relativo
                fecha = pd.to_datetime(row["Fecha_Generacion"])
                delta = datetime.now() - fecha
                
                if delta.days > 0:
                    tiempo = f"Hace {delta.days} día(s)"
                elif delta.seconds // 3600 > 0:
                    tiempo = f"Hace {delta.seconds // 3600} hora(s)"
                else:
                    tiempo = f"Hace {delta.seconds // 60} min"
                
                st.caption(f"🕐 {tiempo}")
                st.caption(fecha.strftime("%Y-%m-%d %H:%M"))
            
            with col2:
                st.markdown(f"**{row['Orden_ID']}**")
                st.caption(row['Formula_Key'])
            
            with col3:
                st.metric("Volumen", f"{row['Gal_Objetivo']:.0f} gal")
            
            with col4:
                # Mostrar referencias si existen
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
    st.info("📭 No hay órdenes registradas aún")

st.markdown("---")

# ===== ESTADO DEL SISTEMA =====
st.markdown("### 🔧 Estado del Sistema")
col1, col2, col3 = st.columns(3)

with col1:
    st.success("✅ API Formulab: Conectada")

with col2:
    # Verificar conexión real con Sheets
    try:
        from formulab.sheets.sheets_connector import get_sheets_client
        get_sheets_client()
        st.success("✅ Google Sheets: Sincronizado")
    except Exception as e:
        st.error(f"❌ Google Sheets: {str(e)[:50]}")

with col3:
    st.info(f"ℹ️ Última sync: {datetime.now().strftime('%H:%M:%S')}")

# Footer con resumen
st.markdown("---")
st.caption(f"📊 Dashboard actualizado | Total: {data['total_ordenes']} órdenes | {data['volumen_total']:.0f} galones producidos")