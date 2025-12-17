"""
Ordenes Manager
---------------
Gestiona la generación y registro de órdenes de producción.
"""

import pandas as pd
from datetime import datetime
from .sheets_connector import get_worksheet, append_sheet, read_sheet
from .formulas_manager import buscar_formula
from formulab.formulab_api import procesar_formula


def _generar_orden_id():
    """
    Genera el próximo Orden_ID secuencial (formato: ORD-2025-001).
    
    Returns:
        str: Próximo ID disponible
    """
    try:
        data = read_sheet("Ordenes_Produccion")
        if len(data) <= 1:
            year = datetime.now().year
            return f"ORD-{year}-001"
        
        # Obtener último ID
        rows = data[1:]
        last_id = rows[-1][0] if rows else f"ORD-{datetime.now().year}-000"
        
        # Extraer número y sumar 1
        parts = last_id.split("-")
        year = parts[1]
        num = int(parts[2]) + 1
        
        return f"ORD-{year}-{num:03d}"
    
    except Exception as e:
        print(f"⚠️ Error generando Orden_ID: {e}")
        year = datetime.now().year
        return f"ORD-{year}-001"


def generar_orden(formula_key, gal_objetivo, ped_id=None, batch_id=None, observaciones=""):
    """
    Genera una orden de producción a partir de una fórmula existente.
    
    Args:
        formula_key (str): ID de la fórmula a usar
        gal_objetivo (float): Galones a producir
        ped_id (str): Referencia a pedido CPG (opcional)
        batch_id (str): Referencia a batch CCP (opcional)
        observaciones (str): Notas especiales (opcional)
    
    Returns:
        tuple: (orden_id, df_escalado, success)
    """
    from .formulas_manager import obtener_ingredientes_formula
    from formulab.core.engine.escalado_core import calcular_escalado
    
    # Buscar fórmula
    formula_data = buscar_formula(formula_key)
    if not formula_data:
        print(f"❌ Fórmula '{formula_key}' no encontrada")
        return None, None, False
    
    # Obtener ingredientes
    df_ingredientes = obtener_ingredientes_formula(formula_key)
    if df_ingredientes.empty:
        print(f"❌ No se encontraron ingredientes para '{formula_key}'")
        return None, None, False
    
    # Renombrar columnas
    df_ingredientes = df_ingredientes.rename(columns={
        "Nombre": "nombre",
        "Cantidad": "CANT",
        "Densidad_KG_GL": "Densidad_KG_GL"
    })
    
    # Datos base
    pg_pintura = float(formula_data.get("PG_Pintura", 5.0))
    
    # Escalar fórmula
    try:
        df_escalado = calcular_escalado(
            ingredientes_df=df_ingredientes,
            gal_objetivo=gal_objetivo,
            pg_pintura=pg_pintura
        )
        
        # Generar Orden_ID
        orden_id = _generar_orden_id()
        
        # Preparar datos
        orden_data = {
            "orden_id": orden_id,
            "formula_key": formula_key,
            "gal_objetivo": gal_objetivo,
            "fecha_generacion": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "ped_id": ped_id or "",
            "batch_id": batch_id or "",
            "observaciones": observaciones or ""
        }
        
        # Registrar orden
        registrar_orden(orden_data)
        
        print(f"✅ Orden '{orden_id}' generada exitosamente")
        
        return orden_id, df_escalado, True
    
    except Exception as e:
        print(f"❌ Error generando orden: {e}")
        return None, None, False
    
def registrar_orden(orden_data):
    """
    Registra una orden en la hoja Ordenes_Produccion.
    
    Args:
        orden_data (dict): Datos de la orden
    """
    orden_row = [
        orden_data["orden_id"],                            # A: Orden_ID
        orden_data["formula_key"],                         # B: Formula_Key
        orden_data["gal_objetivo"],                        # C: Gal_Objetivo
        orden_data["fecha_generacion"],                    # D: Fecha_Generacion
        orden_data.get("ped_id", ""),                      # E: PED_ID
        orden_data.get("batch_id", ""),                    # F: Batch_ID
        orden_data.get("observaciones", "")                # G: Observaciones
    ]
    
    append_sheet("Ordenes_Produccion", orden_row)


def actualizar_estado_orden(orden_id, nuevo_estado, pg_real=None):
    """
    Actualiza el estado de una orden y opcionalmente el P/G real.
    
    Args:
        orden_id (str): ID de la orden
        nuevo_estado (str): Nuevo estado (PENDIENTE, EN_PRODUCCION, COMPLETADO)
        pg_real (float): P/G medido en producción (opcional)
    
    Returns:
        bool: True si se actualizó exitosamente
    """
    try:
        worksheet = get_worksheet("Ordenes_Produccion")
        cell = worksheet.find(orden_id)
        
        if not cell:
            print(f"❌ Orden '{orden_id}' no encontrada")
            return False
        
        # Columna J (estado) es la columna 10
        worksheet.update_cell(cell.row, 10, nuevo_estado)
        
        # Si se proporciona P/G real, actualizar columna G (7)
        if pg_real is not None:
            worksheet.update_cell(cell.row, 7, pg_real)
        
        print(f"✅ Orden '{orden_id}' actualizada a '{nuevo_estado}'")
        return True
    
    except Exception as e:
        print(f"❌ Error actualizando orden: {e}")
        return False


def obtener_ordenes_pendientes():
    """
    Lista todas las órdenes con estado PENDIENTE.
    
    Returns:
        pd.DataFrame: Órdenes pendientes
    """
    try:
        data = read_sheet("Ordenes_Produccion")
        if len(data) <= 1:
            return pd.DataFrame()
        
        df = pd.DataFrame(data[1:], columns=data[0])
        df_pendientes = df[df["Estado"] == "PENDIENTE"]
        
        return df_pendientes
    
    except Exception as e:
        print(f"❌ Error obteniendo órdenes pendientes: {e}")
        return pd.DataFrame()