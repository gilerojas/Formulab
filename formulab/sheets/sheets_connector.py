"""
Google Sheets Connector
-----------------------
Maneja la conexión base con Google Sheets API usando service account.
Soporte para Streamlit Cloud Secrets y desarrollo local.
"""

import gspread
from google.oauth2.service_account import Credentials
import streamlit as st
import os

# Configuración
LOCAL_CREDENTIALS_PATH = "vocal-tracker-453720-p1-2c9dfa471a22.json"
SPREADSHEET_ID = "18Ft7Fn6dxxPgFpYuEx3H_aCBukLdRlpvV1Z2NjUPBvQ"
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]


def get_credentials():
    """Obtiene credenciales desde Streamlit Secrets o archivo local"""
    
    # Streamlit Cloud
    try:
        if hasattr(st, 'secrets') and 'gcp_service_account' in st.secrets:
            return Credentials.from_service_account_info(
                dict(st.secrets['gcp_service_account']),
                scopes=SCOPES
            )
    except Exception:
        pass
    
    # Local
    if os.path.exists(LOCAL_CREDENTIALS_PATH):
        return Credentials.from_service_account_file(
            LOCAL_CREDENTIALS_PATH,
            scopes=SCOPES
        )
    
    raise FileNotFoundError(f"Credentials not found: {LOCAL_CREDENTIALS_PATH}")


def get_sheets_client():
    """Retorna cliente autenticado de gspread"""
    credentials = get_credentials()
    return gspread.authorize(credentials)


def get_spreadsheet(spreadsheet_id=SPREADSHEET_ID):
    """Abre el spreadsheet de Formulab"""
    client = get_sheets_client()
    return client.open_by_key(spreadsheet_id)


def get_worksheet(sheet_name, create_if_missing=True):
    """Obtiene una hoja específica, la crea si no existe"""
    spreadsheet = get_spreadsheet()
    
    try:
        worksheet = spreadsheet.worksheet(sheet_name)
    except gspread.WorksheetNotFound:
        if create_if_missing:
            worksheet = spreadsheet.add_worksheet(title=sheet_name, rows=1000, cols=20)
            print(f"✅ Hoja '{sheet_name}' creada exitosamente")
        else:
            raise
    
    return worksheet


def read_sheet(sheet_name, range_name=None):
    """Lee datos de una hoja"""
    worksheet = get_worksheet(sheet_name, create_if_missing=False)
    
    if range_name:
        values = worksheet.get(range_name)
    else:
        values = worksheet.get_all_values()
    
    return values


def write_sheet(sheet_name, range_name, values):
    """Escribe datos en una hoja (sobrescribe)"""
    worksheet = get_worksheet(sheet_name)
    worksheet.update(range_name, values)


def append_sheet(sheet_name, values):
    """Agrega fila(s) al final de una hoja"""
    worksheet = get_worksheet(sheet_name)
    
    if values and not isinstance(values[0], list):
        values = [values]
    
    worksheet.append_rows(values)


def find_row_index_by_value(sheet_name, column_a_value):
    """
    Busca el índice de la primera fila (1-based) donde la columna A coincide.
    Returns: int or None
    """
    worksheet = get_worksheet(sheet_name, create_if_missing=False)
    data = worksheet.get_all_values()
    if not data:
        return None
    for i, row in enumerate(data):
        if row and str(row[0]).strip() == str(column_a_value).strip():
            return i + 1
    return None


def find_row_indices_by_value(sheet_name, column_index, value):
    """
    Busca todos los índices de fila (1-based) donde la columna dada coincide.
    Returns: list of int
    """
    worksheet = get_worksheet(sheet_name, create_if_missing=False)
    data = worksheet.get_all_values()
    if not data:
        return []
    return [i + 1 for i, row in enumerate(data) if len(row) > column_index and str(row[column_index]).strip() == str(value).strip()]


def update_row(sheet_name, row_index_1based, values):
    """Actualiza una fila por índice (1-based). values: lista de valores por columna."""
    worksheet = get_worksheet(sheet_name)
    if not values:
        return
    if not isinstance(values[0], list):
        values = [values]
    ncols = len(values[0])
    end_col = chr(ord("A") + ncols - 1) if ncols <= 26 else "Z"
    range_name = f"A{row_index_1based}:{end_col}{row_index_1based}"
    worksheet.update(range_name, values)


def delete_rows(sheet_name, start_row_1based, end_row_1based=None):
    """Elimina filas (1-based). Si end_row_1based es None, solo se borra start_row_1based."""
    worksheet = get_worksheet(sheet_name)
    end = end_row_1based if end_row_1based is not None else start_row_1based
    worksheet.delete_rows(start_row_1based, end)


def clear_sheet(sheet_name):
    """Limpia todo el contenido de una hoja"""
    worksheet = get_worksheet(sheet_name, create_if_missing=False)
    worksheet.clear()


def initialize_sheets():
    """Inicializa las hojas necesarias con sus encabezados"""
    
    formulas_headers = [
        "Formula_Key", "Marca", "Tipo", "Color", "Volumen_Base",
        "PG_Pintura", "Total_Ingredientes", "Fecha_Creacion",
        "Observaciones", "Estatus",
    ]
    
    detalle_headers = [
        "Formula_Key", "Linea", "Codigo", "Nombre", "Cantidad",
        "Unidad", "Densidad_KG_GL", "Etapa",
    ]
    
    ordenes_headers = [
        "Orden_ID", "Formula_Key", "Gal_Objetivo", "Gal_Base",
        "Factor_Escala", "PG_Esperado", "PG_Real", "Fecha_Generacion",
        "Generado_Por", "Estado", "PED_ID", "Batch_ID",
    ]
    
    sheets_config = {
        "GREQ_Formulas": formulas_headers,
        "Formulas_Detalle": detalle_headers,
        "Ordenes_Produccion": ordenes_headers,
    }
    
    for sheet_name, headers in sheets_config.items():
        try:
            worksheet = get_worksheet(sheet_name)
            existing_data = worksheet.get_all_values()
            
            if not existing_data or (len(existing_data) == 1 and not any(existing_data[0])):
                worksheet.clear()
                worksheet.append_row(headers)
                print(f"✅ Headers creados en '{sheet_name}'")
            elif len(existing_data) >= 1 and existing_data[0] != headers:
                print(f"⚠️ '{sheet_name}' ya tiene datos. No se modificaron los headers.")
            else:
                print(f"✅ '{sheet_name}' ya inicializada correctamente")
        
        except Exception as e:
            print(f"❌ Error inicializando '{sheet_name}': {e}")


if __name__ == "__main__":
    try:
        client = get_sheets_client()
        spreadsheet = get_spreadsheet()
        print(f"✅ Conexión exitosa a: {spreadsheet.title}")
        print(f"📊 Hojas disponibles: {[ws.title for ws in spreadsheet.worksheets()]}")
        
        initialize_sheets()
    
    except Exception as e:
        print(f"❌ Error de conexión: {e}")