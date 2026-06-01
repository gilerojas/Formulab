"""
Formulas Manager
----------------
Gestiona el CRUD de fórmulas en Google Sheets.
"""

import pandas as pd
from datetime import datetime
from .sheets_connector import get_worksheet, append_sheet, read_sheet, find_row_index_by_value, find_row_indices_by_value, update_row, delete_rows


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


def actualizar_formula(formula_key, formula_meta, df_ingredientes, observaciones=None):
    """
    Actualiza una fórmula existente en Google Sheets (metadata + ingredientes).
    
    Args:
        formula_key (str): Formula_Key a actualizar (debe existir)
        formula_meta (dict): Metadatos con claves Marca, Tipo, Color, Volumen_Base,
                            PG_Pintura, Estatus. Opcional: Observaciones.
        df_ingredientes (pd.DataFrame): DataFrame de ingredientes con columnas
            Formula_Key, Linea, Codigo, Nombre, Cantidad, Unidad, Densidad_KG_GL, Etapa.
        observaciones (str): Si se pasa, sobrescribe formula_meta.get("Observaciones").
    
    Returns:
        tuple: (formula_key, success)
    """
    existing = buscar_formula(formula_key)
    if not existing:
        print(f"⚠️ La fórmula '{formula_key}' no existe. Usa guardar_formula para crear.")
        return formula_key, False

    # Leer ingredientes actuales ANTES de borrar (para el historial)
    df_old_ing = obtener_ingredientes_formula(formula_key)

    obs = observaciones if observaciones is not None else formula_meta.get("Observaciones", "")
    total_ing = len(df_ingredientes)
    
    formula_row = [
        formula_key,
        formula_meta.get("Marca", existing.get("Marca", "N/A")),
        formula_meta.get("Tipo", existing.get("Tipo", "N/A")),
        formula_meta.get("Color", existing.get("Color", "N/A")),
        float(formula_meta.get("Volumen_Base", existing.get("Volumen_Base", 100))),
        float(formula_meta.get("PG_Pintura", existing.get("PG_Pintura", 0))),
        total_ing,
        existing.get("Fecha_Creacion", datetime.now().strftime("%Y-%m-%d %H:%M:%S")),
        obs,
        formula_meta.get("Estatus", existing.get("Estatus", "ACTIVA")),
    ]
    
    row_idx = find_row_index_by_value("GREQ_Formulas", formula_key)
    if not row_idx:
        print(f"❌ No se encontró fila para {formula_key} en GREQ_Formulas")
        return formula_key, False
    
    try:
        update_row("GREQ_Formulas", row_idx, [formula_row])
    except Exception as e:
        print(f"❌ Error actualizando GREQ_Formulas: {e}")
        return formula_key, False
    
    indices = find_row_indices_by_value("Formulas_Detalle", 0, formula_key)
    if indices:
        # Single batch delete — rows are always contiguous (append-only sheet)
        delete_rows("Formulas_Detalle", min(indices), max(indices))
    
    detalle_rows = []
    for idx, row in df_ingredientes.iterrows():
        codigo = str(row.get("Codigo", row.get("CODIGO", ""))).strip() if pd.notna(row.get("Codigo", row.get("CODIGO"))) else ""
        nombre = str(row.get("Nombre", row.get("nombre", ""))).strip() if pd.notna(row.get("Nombre", row.get("nombre"))) else ""
        cant = float(row.get("Cantidad", row.get("CANT", 0))) if pd.notna(row.get("Cantidad", row.get("CANT"))) else 0.0
        unidad = str(row.get("Unidad", "KG")).strip() if pd.notna(row.get("Unidad")) else "KG"
        densidad = float(row.get("Densidad_KG_GL", 0)) if pd.notna(row.get("Densidad_KG_GL")) else 0.0
        etapa = str(row.get("Etapa", "Mezcla")).strip() if pd.notna(row.get("Etapa")) else "Mezcla"
        linea = int(row.get("Linea", idx + 1)) if pd.notna(row.get("Linea")) else int(idx) + 1
        detalle_rows.append([formula_key, linea, codigo, nombre, cant, unidad, densidad, etapa])
    
    if detalle_rows:
        try:
            append_sheet("Formulas_Detalle", detalle_rows)
        except Exception as e:
            print(f"❌ Error actualizando Formulas_Detalle: {e}")
            return formula_key, False
    
    # Registrar historial de cambios
    registrar_historial(formula_key, df_old_ing, df_ingredientes, obs)

    print(f"✅ Fórmula '{formula_key}' actualizada ({total_ing} ingredientes)")
    return formula_key, True


def _compute_change_detail(df_old, df_new):
    """
    Compara ingredientes viejos vs nuevos y devuelve:
      - (n_modified, n_added, n_removed, detalle_str)
    detalle_str: texto compacto para la columna Cambios_Detalle del historial.
    """
    old_map = {}
    for _, row in df_old.iterrows():
        key = str(row.get("Nombre", "")).strip().upper()
        if key:
            old_map[key] = {
                "display": str(row.get("Nombre", "")),
                "cant": float(row.get("Cantidad", 0)) if pd.notna(row.get("Cantidad")) else 0.0,
            }

    new_map = {}
    for _, row in df_new.iterrows():
        nombre_raw = row.get("Nombre", row.get("nombre", ""))
        cant_raw   = row.get("Cantidad", row.get("CANT", 0))
        key = str(nombre_raw).strip().upper()
        if key:
            new_map[key] = {
                "display": str(nombre_raw),
                "cant": float(cant_raw) if pd.notna(cant_raw) else 0.0,
            }

    all_keys = set(old_map) | set(new_map)
    parts = []
    n_modified = n_added = n_removed = 0

    for key in sorted(all_keys):
        in_old = key in old_map
        in_new = key in new_map
        if in_old and in_new:
            old_c = old_map[key]["cant"]
            new_c = new_map[key]["cant"]
            if abs(new_c - old_c) > 1e-6:
                n_modified += 1
                sign = "+" if (new_c - old_c) > 0 else ""
                parts.append(f"{new_map[key]['display']}: {old_c:.2f}→{new_c:.2f} ({sign}{new_c - old_c:.2f})")
        elif in_old:
            n_removed += 1
            parts.append(f"-{old_map[key]['display']}")
        else:
            n_added += 1
            parts.append(f"+{new_map[key]['display']}")

    detalle = " | ".join(parts) if parts else "Sin cambios en ingredientes"
    return n_modified, n_added, n_removed, detalle


def registrar_historial(formula_key, df_old, df_new, observaciones=""):
    """
    Agrega una fila de auditoría a la hoja Formula_Historial.
    Se llama después de cada actualización exitosa.
    """
    n_modified, n_added, n_removed, detalle = _compute_change_detail(df_old, df_new)

    historial_row = [
        formula_key,                                        # A: Formula_Key
        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),       # B: Fecha_Modificacion
        len(df_old),                                        # C: Ingredientes_Antes
        len(df_new),                                        # D: Ingredientes_Despues
        n_modified,                                         # E: Modificados
        n_added,                                            # F: Nuevos
        n_removed,                                          # G: Removidos
        observaciones,                                      # H: Observaciones
        detalle,                                            # I: Cambios_Detalle
    ]

    try:
        append_sheet("Formula_Historial", historial_row)
        print(f"✅ Historial registrado para '{formula_key}'")
    except Exception as e:
        # No crítico — no falla el update si el historial falla
        print(f"⚠️ No se pudo registrar historial: {e}")


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
        for col in ["Formula_Key", "Marca", "Tipo", "Estatus"]:
            if col in df.columns:
                df[col] = df[col].fillna("").astype(str).str.strip()
        
        # Aplicar filtros
        if estatus and "Estatus" in df.columns:
            estatus_norm = str(estatus).strip().upper()
            df = df[df["Estatus"].str.upper() == estatus_norm]
        if marca and "Marca" in df.columns:
            marca_norm = str(marca).strip().upper()
            df = df[df["Marca"].str.upper() == marca_norm]
        if tipo and "Tipo" in df.columns:
            tipo_norm = str(tipo).strip().upper()
            df = df[df["Tipo"].str.upper() == tipo_norm]
        
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


def obtener_impacto_eliminacion_formula(formula_key):
    """
    Devuelve el alcance exacto de una eliminación sin modificar Google Sheets.

    Solo cuenta coincidencias exactas de Formula_Key en:
      - GREQ_Formulas, columna A
      - Formulas_Detalle, columna A
    """
    formula_key = str(formula_key).strip()
    if not formula_key:
        return {
            "formula_key": "",
            "formula_rows": [],
            "detalle_rows": [],
            "can_delete": False,
            "reason": "Formula_Key vacío",
        }

    formula_rows = find_row_indices_by_value("GREQ_Formulas", 0, formula_key)
    detalle_rows = find_row_indices_by_value("Formulas_Detalle", 0, formula_key)

    can_delete = len(formula_rows) == 1
    reason = ""
    if len(formula_rows) == 0:
        reason = "No existe una fila exacta en GREQ_Formulas"
    elif len(formula_rows) > 1:
        reason = "Hay más de una fila exacta en GREQ_Formulas; requiere revisión manual"

    return {
        "formula_key": formula_key,
        "formula_rows": formula_rows,
        "detalle_rows": detalle_rows,
        "can_delete": can_delete,
        "reason": reason,
    }


def eliminar_formula(formula_key, confirm_formula_key):
    """
    Elimina una fórmula exacta del catálogo.

    Precisión:
      - Requiere confirmación textual idéntica al Formula_Key.
      - Borra solo coincidencias exactas en columna A.
      - Borra filas de abajo hacia arriba para no desplazar índices pendientes.
      - No toca órdenes, historial ni otras hojas.
    """
    formula_key = str(formula_key).strip()
    confirm_formula_key = str(confirm_formula_key).strip()

    if formula_key != confirm_formula_key:
        return False, "La confirmación no coincide exactamente con el Formula_Key.", {}

    impacto = obtener_impacto_eliminacion_formula(formula_key)
    if not impacto["can_delete"]:
        return False, impacto["reason"], impacto

    try:
        for row_idx in sorted(impacto["detalle_rows"], reverse=True):
            delete_rows("Formulas_Detalle", row_idx)

        for row_idx in sorted(impacto["formula_rows"], reverse=True):
            delete_rows("GREQ_Formulas", row_idx)

        return True, "Fórmula eliminada correctamente.", impacto
    except Exception as e:
        return False, f"Error eliminando fórmula: {e}", impacto
