"""
Tipo Mapeo Manager - v2.0
-------------------------
Gestiona mapeo de tipos → tags (SIN marca).
22 tipos de pintura GREQ actualizados.
"""

import pandas as pd
from .sheets_connector import get_worksheet, append_sheet, read_sheet

# ========== MAPEO COMPLETO GREQ ==========
# Diccionario completo con 21 tipos
TIPOS_MAPEO_GREQ = {
    "ACRILICA SUPERIOR HP": "HP",
    "ACRILICA SUPERIOR TIPO B": "SUP-B",
    "BARNIZ CLEAR INDUSTRIAL": "BCL",
    "BARNIZ PORT EPOXI CLEAR": "BEP",
    "DRY WET": "DRY",
    "ECONOMICA": "ECO",
    "EPOXICA": "EPO",
    "ESMALTE INDUSTRIAL": "EIN",
    "ESMALTE INDUSTRIAL ANTICORROSIVO": "EANT",
    "ESMALTE MANTENIMIENTO": "EMAN",
    "ESMALTE TRAFICO": "ETR",
    "PINTURA P/ CANCHA": "PCA",
    "PRIMER ACRILICO": "PRI",
    "PROYECTO CONTRACTOR": "PRO",
    "PROYECTO P/ TECHOS": "PTE",
    "SATINADA": "SAT",
    "SEALER WATER": "SEW",
    "SELLADOR P/ PISOS": "SPP",
    "SELLADOR TECHOS HP": "SLP",
    "SELLADOR TECHOS TIPO B": "SLT",
    "SEMIGLOSS PREMIUM": "SEM-P",
    "SEMIGLOSS TIPO B": "SEM-B",
    "TEXTURIZADAS": "TXT"
}

def _normalizar_tipo(texto):
    """Normaliza nombre de tipo para matching."""
    import re
    texto = texto.upper().strip()
    texto = re.sub(r'\s+', ' ', texto)
    return texto


def obtener_mapeo_tipos():
    """
    Retorna DataFrame con tipos GREQ.
    
    Returns:
        pd.DataFrame: [Tipo_Completo, Tipo_Tag, Tipo_Normalizado]
    """
    try:
        data = read_sheet("Tipo_Mapeo")
        
        if len(data) <= 1:
            print("⚠️ Hoja 'Tipo_Mapeo' vacía, usando mapeo por defecto")
            return _crear_mapeo_default()
        
        df = pd.DataFrame(data[1:], columns=data[0])
        df["Tipo_Normalizado"] = df["Tipo_Completo"].apply(_normalizar_tipo)
        
        return df
    
    except Exception as e:
        print(f"❌ Error leyendo Tipo_Mapeo: {e}")
        return _crear_mapeo_default()


def _crear_mapeo_default():
    """Crea DataFrame con 22 tipos GREQ."""
    df = pd.DataFrame([
        {"Tipo_Completo": tipo, "Tipo_Tag": tag}
        for tipo, tag in TIPOS_MAPEO_GREQ.items()
    ])
    
    df["Tipo_Normalizado"] = df["Tipo_Completo"].apply(_normalizar_tipo)
    return df


def obtener_lista_tipos():
    """
    Retorna lista ordenada de tipos para dropdown.
    
    Returns:
        list: Nombres completos ordenados alfabéticamente
    """
    df = obtener_mapeo_tipos()
    return sorted(df["Tipo_Completo"].tolist())


def buscar_tipo_tag(tipo_raw, mapeo_df=None):
    """
    Busca el Tipo_Tag correspondiente a un tipo de pintura.
    
    Args:
        tipo_raw (str): Tipo de pintura
        mapeo_df (pd.DataFrame): DataFrame de mapeo (opcional)
    
    Returns:
        tuple: (tipo_tag, encontrado)
               ej: ("HP", True) o ("GEN", False)
    """
    if mapeo_df is None:
        mapeo_df = obtener_mapeo_tipos()
    
    tipo_norm = _normalizar_tipo(tipo_raw)
    
    # Búsqueda exacta
    match = mapeo_df[mapeo_df["Tipo_Normalizado"] == tipo_norm]
    
    if not match.empty:
        return (match.iloc[0]["Tipo_Tag"], True)
    
    # Búsqueda fuzzy por palabras clave
    for idx, row in mapeo_df.iterrows():
        tipo_completo = row["Tipo_Normalizado"]
        
        # Match por contenido
        if tipo_completo in tipo_norm or tipo_norm in tipo_completo:
            return (row["Tipo_Tag"], True)
        
        # Match por palabras clave principales
        palabras_tipo = set(tipo_completo.split())
        palabras_raw = set(tipo_norm.split())
        
        # Si coinciden 2+ palabras significativas
        palabras_comunes = palabras_tipo & palabras_raw
        palabras_importantes = palabras_comunes - {"DE", "PARA", "O", "P/"}
        
        if len(palabras_importantes) >= 2:
            return (row["Tipo_Tag"], True)
    
    # No encontrado
    return ("GEN", False)


def get_tipo_tag_directo(tipo_completo):
    """
    Obtiene tag directo desde el mapeo (sin fuzzy matching).
    Usar cuando el tipo viene del dropdown.
    
    Args:
        tipo_completo (str): Nombre exacto del tipo
    
    Returns:
        str: Tipo_Tag o "GEN"
    """
    return TIPOS_MAPEO_GREQ.get(tipo_completo.upper(), "GEN")


def sugerir_tipo_tag(tipo_completo):
    """
    Sugiere un Tipo_Tag basado en el nombre del tipo.
    Útil cuando se detecta un tipo nuevo no registrado.
    
    Args:
        tipo_completo (str): Nombre del tipo (ej: "ESMALTE ANTICORROSIVO")
    
    Returns:
        str: Tag sugerido (ej: "EANT")
    
    Examples:
        >>> sugerir_tipo_tag("ESMALTE ANTICORROSIVO")
        'EANT'
        >>> sugerir_tipo_tag("ACRILICA SUPERIOR")
        'ASUP'
        >>> sugerir_tipo_tag("BARNIZ")
        'BAR'
    """
    import re
    
    tipo_norm = _normalizar_tipo(tipo_completo)
    
    # Filtrar palabras irrelevantes
    palabras_filtradas = [
        w for w in tipo_norm.split() 
        if w not in ["DE", "PARA", "TIPO", "LA", "EL", "INFINITI", "MILAN", "O", "P/"]
    ]
    
    # Estrategia según número de palabras
    if len(palabras_filtradas) == 0:
        return "GEN"
    
    elif len(palabras_filtradas) == 1:
        # Una palabra → primeras 3 letras
        return palabras_filtradas[0][:3]
    
    elif len(palabras_filtradas) == 2:
        # Dos palabras → 1ra letra + 2 letras de segunda
        return palabras_filtradas[0][0] + palabras_filtradas[1][:2]
    
    else:
        # 3+ palabras → primera letra de cada una
        return "".join([p[0] for p in palabras_filtradas[:3]])


def registrar_tipo_nuevo(tipo_completo, tipo_tag):
    """
    Registra un nuevo tipo en Tipo_Mapeo (admin).
    
    Args:
        tipo_completo (str): Nombre completo (ej: "ESMALTE ANTICORROSIVO")
        tipo_tag (str): Tag corto (ej: "EANT")
    
    Returns:
        bool: True si se registró exitosamente
    """
    try:
        tipo_completo = _normalizar_tipo(tipo_completo)
        tipo_tag = tipo_tag.upper().strip()
        
        # Validar duplicados
        mapeo = obtener_mapeo_tipos()
        if tipo_completo in mapeo["Tipo_Normalizado"].values:
            print(f"⚠️ Tipo '{tipo_completo}' ya existe")
            return False
        
        # Agregar a Sheets
        nueva_fila = [tipo_completo, tipo_tag]
        append_sheet("Tipo_Mapeo", nueva_fila)
        
        print(f"✅ Tipo '{tipo_completo}' registrado con tag '{tipo_tag}'")
        return True
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return False


def inicializar_tipo_mapeo():
    """Inicializa la hoja Tipo_Mapeo (ejecutar UNA VEZ)."""
    try:
        # Verificar si existe
        try:
            data = read_sheet("Tipo_Mapeo")
            if len(data) > 1:
                print("✅ Hoja 'Tipo_Mapeo' ya existe")
                return
        except:
            pass
        
        # Crear hoja
        worksheet = get_worksheet("Tipo_Mapeo")
        
        # Header
        header = ["Tipo_Completo", "Tipo_Tag"]
        worksheet.append_row(header)
        
        # Datos default (22 tipos)
        df_default = _crear_mapeo_default()
        for _, row in df_default.iterrows():
            worksheet.append_row([
                row["Tipo_Completo"],
                row["Tipo_Tag"]
            ])
        
        print("✅ Hoja 'Tipo_Mapeo' inicializada con 22 tipos GREQ")
    
    except Exception as e:
        print(f"❌ Error: {e}")