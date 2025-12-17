"""
Gestor de caché para datos y fórmulas
"""
import streamlit as st
from datetime import datetime, timedelta
import json


class CacheManager:
    """Maneja caché de fórmulas y sesiones"""
    
    CACHE_KEY_FORMULAS = "formulab_formulas_cache"
    CACHE_KEY_TIMESTAMP = "formulab_cache_timestamp"
    CACHE_TTL = 3600  # 1 hora
    
    @staticmethod
    def get_cached_formulas():
        """Obtiene fórmulas del caché"""
        if CacheManager.CACHE_KEY_FORMULAS not in st.session_state:
            return None
        
        cache_data = st.session_state[CacheManager.CACHE_KEY_FORMULAS]
        timestamp = st.session_state.get(CacheManager.CACHE_KEY_TIMESTAMP)
        
        if timestamp:
            elapsed = (datetime.now() - datetime.fromisoformat(timestamp)).total_seconds()
            if elapsed > CacheManager.CACHE_TTL:
                return None
        
        return cache_data
    
    @staticmethod
    def set_cached_formulas(formulas: list):
        """Guarda fórmulas en caché"""
        st.session_state[CacheManager.CACHE_KEY_FORMULAS] = formulas
        st.session_state[CacheManager.CACHE_KEY_TIMESTAMP] = datetime.now().isoformat()
    
    @staticmethod
    def clear_cache():
        """Limpia el caché"""
        if CacheManager.CACHE_KEY_FORMULAS in st.session_state:
            del st.session_state[CacheManager.CACHE_KEY_FORMULAS]
        if CacheManager.CACHE_KEY_TIMESTAMP in st.session_state:
            del st.session_state[CacheManager.CACHE_KEY_TIMESTAMP]