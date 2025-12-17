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

# ===== SISTEMA DE LOGIN =====
def check_password():
    """Verifica contraseña"""
    
    if st.session_state.get("authenticated", False):
        return True
    
    # Aplicar estilos para login
    apply_custom_css()
    
    st.markdown("# 🔐 Formulab - GREQ")
    st.markdown("### Sistema de Fórmulas de Producción")
    st.markdown("---")
    
    col1, col2, col3 = st.columns([1, 2, 1])
    
    with col2:
        password = st.text_input(
            "Contraseña:",
            type="password",
            key="password_input"
        )
        
        if st.button("Iniciar Sesión", use_container_width=True, type="primary"):
            if password == "Woltemade27":
                st.session_state["authenticated"] = True
                st.rerun()
            else:
                st.error("❌ Contraseña incorrecta")
    
    st.markdown("---")
    st.caption("🏭 GR Especialidades Químicas (GREQ)")
    
    return False

# Verificar autenticación
if not check_password():
    st.stop()

# ===== APP PRINCIPAL =====
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

# Botón logout
if st.sidebar.button("🚪 Cerrar Sesión", use_container_width=True):
    st.session_state["authenticated"] = False
    st.rerun()

st.sidebar.markdown("---")

# Navigation
st.sidebar.markdown("### 📑 Navegación")

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

st.session_state.current_page = list(pages.values())[list(pages.keys()).index(selected)]

# Footer sidebar
st.sidebar.markdown("---")
st.sidebar.markdown("""
**Soporte:**
- 📧 [gilerojas@gmail.com](mailto:gilerojas@gmail.com)
- 🔧 Sistema GREQ v6.3
""")

st.info("ℹ️ Usa el selector de la izquierda para navegar entre secciones")