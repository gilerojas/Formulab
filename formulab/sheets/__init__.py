"""
Formulab Sheets Integration
----------------------------
Módulo de integración con Google Sheets para GREQ.
"""

from .sheets_connector import (
    get_sheets_client,
    get_spreadsheet,
    get_worksheet,
    read_sheet,
    write_sheet,
    append_sheet,
    clear_sheet,
    initialize_sheets
)

from .formulas_manager import (
    guardar_formula,
    buscar_formula,
    listar_formulas,
    obtener_ingredientes_formula
)

from .ordenes_manager import (
    generar_orden,
    registrar_orden,
    actualizar_estado_orden,
    obtener_ordenes_pendientes
)

__all__ = [
    # Connector
    'get_sheets_client',
    'get_spreadsheet',
    'get_worksheet',
    'read_sheet',
    'write_sheet',
    'append_sheet',
    'clear_sheet',
    'initialize_sheets',
    
    # Formulas Manager
    'guardar_formula',
    'buscar_formula',
    'listar_formulas',
    'obtener_ingredientes_formula',
    
    # Ordenes Manager
    'generar_orden',
    'registrar_orden',
    'actualizar_estado_orden',
    'obtener_ordenes_pendientes'
]