"""
Formulab - Sistema de Fórmulas GREQ
Launcher principal de la aplicación Streamlit
"""
import streamlit as st
from utils.styling import apply_custom_css, COLORS

# Configuración de página
st.set_page_config(
    page_title="🧪 Formulab - GREQ",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Aplicar estilos globales
apply_custom_css()

# Session state
if "user" not in st.session_state:
    st.session_state.user = "operario"
if "current_page" not in st.session_state:
    st.session_state.current_page = "home"

# Sidebar con navegación
st.sidebar.markdown("# 🧪 FORMULAB")
st.sidebar.markdown(f"**Versión:** 1.0.0")
st.sidebar.markdown(f"**Empresa:** GREQ")
st.sidebar.markdown("---")

# Navigation - CAMBIAR ESTO
st.sidebar.markdown("### 📑 Navegación")

# Mapeo de páginas (nombres nuevos)
pages = {
    "🏠 Home": "pages/home",
    "📝 Nueva Fórmula": "pages/nueva_formula",
    "📚 Catálogo": "pages/catalogo",
    "🏭 Generar Orden": "pages/generar_orden"
}

selected = st.sidebar.radio(
    "Selecciona una sección:",
    options=list(pages.keys()),
    label_visibility="collapsed"
)

# Guardar página actual
st.session_state.current_page = list(pages.values())[list(pages.keys()).index(selected)]

# Footer sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Soporte:**
- 📧 [gilerojas@gmail.com](mailto:gilerojas@gmail.com)
- 🔧 Sistema GREQ v6.3
""")

# Nota: Las páginas se cargan automáticamente desde pages/ folder
st.info("ℹ️ Usa el selector de la izquierda para navegar entre secciones")