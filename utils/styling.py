"""
Styling utilities para Formulab
Paleta de colores GREQ oficial
"""

import streamlit as st

# 🎨 Paleta de colores GREQ oficial
COLORS = {
    "primary": "#B65A2A",      # Cobre/Naranja quemado
    "secondary": "#3B3B3B",    # Gris oscuro (texto principal)
    "accent": "#6E6E6E",       # Gris medio
    "background": "#F6F6F6",   # Blanco cálido
    "success": "#10B981",      # Verde
    "warning": "#F59E0B",      # Amarillo
    "error": "#EF4444",        # Rojo
    "danger": "#EF4444",       # Alias para error
    "info": "#3B82F6",         # Azul
}

def apply_custom_css():
    """Aplica estilos CSS personalizados con colores GREQ"""
    st.markdown(f"""
    <style>
        :root {{
            --primary: {COLORS['primary']};
            --secondary: {COLORS['secondary']};
            --accent: {COLORS['accent']};
            --background: {COLORS['background']};
            --success: {COLORS['success']};
            --warning: {COLORS['warning']};
            --error: {COLORS['error']};
            --danger: {COLORS['danger']};
            --info: {COLORS['info']};
        }}
        
        /* Headers personalizados */
        h1, h2, h3 {{
            color: {COLORS['primary']};
        }}
        
        /* Contenedores con borde */
        .stMarkdown {{
            color: {COLORS['secondary']};
        }}
        
        /* Tablas */
        .dataframe {{
            border-color: {COLORS['accent']} !important;
        }}
    </style>
    """, unsafe_allow_html=True)


def render_header(title, subtitle="", emoji=""):
    """Renderiza un header consistente con colores GREQ"""
    if emoji:
        st.markdown(f"# {emoji} {title}")
    else:
        st.markdown(f"# {title}")
    
    if subtitle:
        st.markdown(f"**{subtitle}**")
    
    st.markdown("---")