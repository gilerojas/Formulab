"""
Tarjetas reutilizables para métricas y status
"""
import streamlit as st


def MetricCard(label: str, value: str | int | float, delta: str = None, 
               color: str = "🟢", icon: str = "📊"):
    """
    Renderiza una card de métrica estilo dashboard.
    
    Args:
        label: Texto de etiqueta
        value: Valor a mostrar (número grande)
        delta: Cambio respecto a período anterior (ej: "+5%")
        color: Emoji de color
        icon: Emoji decorativo
    """
    col1, col2 = st.columns([1, 3])
    
    with col1:
        st.markdown(f"<h2 style='text-align: center'>{icon}</h2>", 
                   unsafe_allow_html=True)
    
    with col2:
        st.markdown(f"**{label}**")
        st.markdown(f"<h3 style='margin: 0; color: #1E3A8A'>{value}</h3>", 
                   unsafe_allow_html=True)
        if delta:
            st.caption(f"({delta})")


def StatusCard(title: str, status: str, details: dict = None):
    """
    Renderiza una card de status con información.
    
    Args:
        title: Título de la card
        status: "✅", "⚠️", "❌", "🔄"
        details: Diccionario {label: value} con información adicional
    """
    with st.container(border=True):
        col1, col2 = st.columns([1, 5])
        
        with col1:
            st.markdown(f"<h2>{status}</h2>", unsafe_allow_html=True)
        
        with col2:
            st.markdown(f"**{title}**")
        
        if details:
            for key, val in details.items():
                st.caption(f"**{key}:** {val}")


def AlertCard(message: str, alert_type: str = "info"):
    """
    Renderiza una alerta con color según tipo.
    
    Args:
        message: Texto del mensaje
        alert_type: "success", "warning", "error", "info"
    """
    colors = {
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
        "info": "#3B82F6"
    }
    icons = {
        "success": "✅",
        "warning": "⚠️",
        "error": "❌",
        "info": "ℹ️"
    }
    
    color = colors.get(alert_type, colors["info"])
    icon = icons.get(alert_type, icons["info"])
    
    st.markdown(f"""
    <div style='padding: 12px; background-color: {color}20; border-left: 4px solid {color}; 
                border-radius: 4px; margin: 10px 0'>
        <span style='color: {color}'>{icon} {message}</span>
    </div>
    """, unsafe_allow_html=True)