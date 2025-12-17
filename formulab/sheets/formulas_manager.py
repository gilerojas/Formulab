"""
Formulas Manager
----------------
Gestiona el CRUD de fórmulas en Google Sheets.
"""

import pandas as pd
from datetime import datetime
from .sheets_connector import get_worksheet, append_sheet, read_sheet


def guardar_formula(result, observaciones=""):
    """
    Guarda una fórmula procesada en Google Sheets.
    
    Args:
        result (dict): Resultado de procesar_formula()
        observaciones (str): Notas técnicas adicionales
    
    Returns:
        tuple: (formula_key, success)
    """
    meta = result["meta"]
    fkey = result["formula_key"]
    df_escalado = result["df_escalado"]
    
    print(f"\n🔍 DEBUG guardar_formula:")
    print(f"  - Formula Key: {fkey}")
    print(f"  - Total ingredientes: {len(df_escalado)}")
    print(f"  - Columnas DF: {df_escalado.columns.tolist()}")
    
    # Verificar si ya existe
    existing = buscar_formula(fkey)
    if existing:
        print(f"⚠️ La fórmula '{fkey}' ya existe en el catálogo.")
        return fkey, False
    
    # Preparar fila para GREQ_Formulas (10 columnas)
    formula_row = [
        fkey,                                           # A: Formula_Key
        meta.get("marca", "N/A"),                       # B: Marca
        meta.get("tipo", "N/A"),                        # C: Tipo
        meta.get("color", "N/A"),                       # D: Color
        float(meta.get("gal_producir", 0)),            # E: Volumen_Base
        float(meta.get("P/G", 0)),                     # F: PG_Pintura
        len(df_escalado),                               # G: Total_Ingredientes
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),   # H: Fecha_Creacion
        observaciones,                                  # I: Observaciones
        "ACTIVA"                                        # J: Estatus
    ]
    
    print(f"\n📝 Fila GREQ_Formulas: {formula_row}")
    
    # Guardar en GREQ_Formulas
    try:
        append_sheet("GREQ_Formulas", formula_row)
        print(f"✅ Guardado en GREQ_Formulas")
    except Exception as e:
        print(f"❌ Error guardando en GREQ_Formulas: {e}")
        import traceback
        traceback.print_exc()
        return fkey, False
    
    # Guardar ingredientes en Formulas_Detalle
    detalle_rows = []
    
    print(f"\n🔍 Procesando {len(df_escalado)} ingredientes:")
    
    for idx, row in df_escalado.iterrows():
        # Acceso directo a columnas
        codigo = str(row["CODIGO"]) if "CODIGO" in df_escalado.columns and pd.notna(row["CODIGO"]) else ""
        nombre = str(row["nombre"]) if "nombre" in df_escalado.columns and pd.notna(row["nombre"]) else ""
        cant = float(row["CANT"]) if "CANT" in df_escalado.columns and pd.notna(row["CANT"]) else 0.0
        unidad = str(row.get("Unidad", "KG")) if pd.notna(row.get("Unidad")) else "KG"
        densidad = float(row["Densidad_KG_GL"]) if "Densidad_KG_GL" in df_escalado.columns and pd.notna(row["Densidad_KG_GL"]) else 0.0
        
        # Para etapa, probar ambas variantes
        etapa = "Mezcla"
        if "etapa" in df_escalado.columns and pd.notna(row["etapa"]):
            etapa = str(row["etapa"])
        elif "Etapa" in df_escalado.columns and pd.notna(row["Etapa"]):
            etapa = str(row["Etapa"])
        
        detalle_row = [
            fkey,           # A: Formula_Key
            int(idx + 1),   # B: Linea
            codigo,         # C: Codigo
            nombre,         # D: Nombre
            cant,           # E: Cantidad
            unidad,         # F: Unidad
            densidad,       # G: Densidad_KG_GL
            etapa           # H: Etapa
        ]
        
        detalle_rows.append(detalle_row)
        
        # Debug primera y última fila
        if idx == 0 or idx == len(df_escalado) - 1:
            print(f"  Fila {idx + 1}: {detalle_row}")
    
    print(f"\n📝 Total filas para Formulas_Detalle: {len(detalle_rows)}")
    
    # Guardar en Formulas_Detalle
    try:
        append_sheet("Formulas_Detalle", detalle_rows)
        print(f"✅ Guardado en Formulas_Detalle")
    except Exception as e:
        print(f"❌ Error guardando en Formulas_Detalle: {e}")
        import traceback
        traceback.print_exc()
        return fkey, False
    
    print(f"\n✅ Fórmula '{fkey}' guardada exitosamente ({len(detalle_rows)} ingredientes)")
    return fkey, True

def buscar_formula(formula_key):
    """
    Busca una fórmula por su Formula_Key.
    
    Args:
        formula_key (str): ID único de la fórmula (ej: PM-SUP-BLANCO100-66)
    
    Returns:
        dict or None: Datos de la fórmula si existe, None si no se encuentra
    """
    try:
        data = read_sheet("GREQ_Formulas")
        
        # Debug: mostrar lo que se lee
        print(f"🔍 DEBUG buscar_formula:")
        print(f"  - Buscando: '{formula_key}'")
        print(f"  - Filas leídas: {len(data)}")
        
        if len(data) <= 1:  # Solo headers o vacío
            print(f"  ⚠️ Hoja vacía o solo con headers")
            return None
        
        headers = data[0]
        rows = data[1:]
        
        print(f"  - Headers: {headers[:3]}...")  # Mostrar primeros 3 headers
        print(f"  - Primera fila: {rows[0][:3] if rows else 'N/A'}...")
        
        for row in rows:
            if len(row) > 0 and row[0] == formula_key:  # Columna A: Formula_Key
                print(f"  ✅ Fórmula encontrada!")
                return dict(zip(headers, row))
        
        print(f"  ❌ Fórmula NO encontrada")
        print(f"  - Keys disponibles: {[r[0] for r in rows if len(r) > 0]}")
        return None
    
    except Exception as e:
        print(f"❌ Error buscando fórmula: {e}")
        import traceback
        traceback.print_exc()
        return None


def listar_formulas(marca=None, tipo=None, estatus="ACTIVA"):
    """
    Lista fórmulas con filtros opcionales.
    
    Args:
        marca (str): Filtrar por marca (MILAN, INFINITI)
        tipo (str): Filtrar por tipo
        estatus (str): Filtrar por estatus (default: ACTIVA)
    
    Returns:
        pd.DataFrame: DataFrame con las fórmulas que cumplen los filtros
    """
    try:
        data = read_sheet("GREQ_Formulas")
        if len(data) <= 1:
            return pd.DataFrame()
        
        df = pd.DataFrame(data[1:], columns=data[0])
        
        # Aplicar filtros
        if estatus:
            df = df[df["Estatus"] == estatus]
        if marca:
            df = df[df["Marca"] == marca]
        if tipo:
            df = df[df["Tipo"] == tipo]
        
        return df
    
    except Exception as e:
        print(f"❌ Error listando fórmulas: {e}")
        return pd.DataFrame()

def obtener_ingredientes_formula(formula_key):
    """
    Obtiene los ingredientes de una fórmula desde Formulas_Detalle.
    
    Args:
        formula_key (str): ID de la fórmula
    
    Returns:
        pd.DataFrame: DataFrame con los ingredientes
    """
    try:
        data = read_sheet("Formulas_Detalle")
        if len(data) <= 1:
            return pd.DataFrame()
        
        df = pd.DataFrame(data[1:], columns=data[0])
        df_formula = df[df["Formula_Key"] == formula_key]
        
        # Convertir tipos numéricos
        numeric_cols = ["Linea", "Cantidad", "Densidad_KG_GL"]
        for col in numeric_cols:
            if col in df_formula.columns:
                df_formula[col] = pd.to_numeric(df_formula[col], errors='coerce')
        
        return df_formula.sort_values("Linea")
    
    except Exception as e:
        print(f"❌ Error obteniendo ingredientes: {e}")
        return pd.DataFrame()
