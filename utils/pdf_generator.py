"""
PDF Generator para Órdenes de Producción - GREQ
------------------------------------------------
Versión: 3.0 (Layout inteligente – toda la fórmula en una hoja)
Cambios en v3.0:
- ✅ Sin truncado: todos los ingredientes siempre en una sola hoja
- ✅ Escalado inteligente: tamaño de fuente y padding según cantidad de items
- ✅ Más legible con pocos items (fuente grande); compacto con muchos
- ✅ Altura disponible calculada a partir de márgenes y bloques fijos

Autor: Gilberto Rojas
Empresa: GR Especialidades Químicas
Fecha: Diciembre 2025
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT
from datetime import datetime
import math
import os

# 🎨 Paleta de colores GREQ oficial
COLOR_COBRE = colors.HexColor("#B65A2A")
COLOR_GRIS_OSCURO = colors.HexColor("#3B3B3B")
COLOR_GRIS_MEDIO = colors.HexColor("#6E6E6E")
COLOR_GRIS_CLARO = colors.HexColor("#F0F0F0")
COLOR_FONDO = colors.HexColor("#F6F6F6")

# 📐 Constantes de layout para "una hoja" (letter = 8.5" x 11") - aprovechar al máximo
PAGE_HEIGHT_INCH = letter[1] / 72.0  # 11"
MARGIN_INCH = 0.4  # márgenes reducidos para más espacio útil
MARGIN_TOP_BOTTOM_INCH = MARGIN_INCH * 2
# Bloques fijos compactos (header, info, subtitle, firma, footer)
FIXED_BLOCKS_INCH = 1.9
AVAILABLE_TABLE_INCH = PAGE_HEIGHT_INCH - MARGIN_TOP_BOTTOM_INCH - FIXED_BLOCKS_INCH
AVAILABLE_TABLE_PT = AVAILABLE_TABLE_INCH * 72
FONT_MIN, FONT_MAX = 5, 13  # rango amplio: más legible con pocos items


def _compute_table_layout(n_rows: int):
    """
    Calcula tamaño de fuente y padding para la tabla de ingredientes
    de forma que quepa en una sola hoja y sea lo más legible posible.

    n_rows: número total de filas de la tabla (cabecera + datos + fila total).
    Returns: dict con fontSize_header, fontSize_codigo, fontSize_nombre, fontSize_nums, padding_pt
    """
    if n_rows <= 0:
        n_rows = 1
    height_per_row_pt = AVAILABLE_TABLE_PT / n_rows
    # Altura de una fila ≈ leading + 2*padding. leading ≈ fontSize * 1.2
    # Queremos fontSize*1.2 + 2*padding <= height_per_row_pt
    padding_pt = 1
    # fontSize máximo que cabe en esta fila
    font_calc = (height_per_row_pt - 2 * padding_pt) / 1.2
    font_clamped = max(FONT_MIN, min(FONT_MAX, int(math.floor(font_calc))))
    if font_clamped <= 6:
        padding_pt = 0
        font_clamped = max(FONT_MIN, min(FONT_MAX, int((height_per_row_pt - 2) / 1.2)))
    return {
        "fontSize_header": font_clamped,
        "fontSize_codigo": max(FONT_MIN, font_clamped - 1),
        "fontSize_nombre": font_clamped,
        "fontSize_nums": min(FONT_MAX, font_clamped + 1),
        "fontSize_etapa": font_clamped,
        "padding_pt": max(0, padding_pt),
    }

def generar_pdf_orden(
    orden_id: str,
    formula_info: dict,
    df_escalado,
    galones_objetivo: float,
    ped_id: str = "",
    batch_id: str = "",
    observaciones: str = "",
    output_path: str = None
):
    """
    Genera PDF de orden de producción (GARANTIZADO en 1 página).
    
    Args:
        orden_id: ID de la orden (ej: "ORD-2025-001")
        formula_info: Dict con Formula_Key, Marca, Tipo, Color, PG_Pintura
        df_escalado: DataFrame con columnas: etapa, CODIGO, nombre, KG_PRO, GL_PRO
        galones_objetivo: Volumen total a producir
        ped_id: ID de pedido (opcional)
        batch_id: ID de batch (opcional)
        observaciones: Notas adicionales (opcional)
        output_path: Ruta de salida (opcional, por defecto /tmp/)
    
    Returns:
        str: Ruta del archivo PDF generado
    """
    
    if not output_path:
        output_path = f"/tmp/orden_{orden_id}.pdf"
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=MARGIN_INCH*inch,
        leftMargin=MARGIN_INCH*inch,
        topMargin=MARGIN_INCH*inch,
        bottomMargin=MARGIN_INCH*inch,
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=12,
        textColor=COLOR_COBRE,
        spaceAfter=1,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
    )
    
    style_subtitle = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=8,
        textColor=COLOR_GRIS_OSCURO,
        spaceAfter=2,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
    )
    
    style_normal = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=7,
        spaceAfter=2,
        textColor=COLOR_GRIS_OSCURO
    )
    
    # ===== HEADER COMPACTO =====
    header_data = [
        [Paragraph("ORDEN DE PRODUCCIÓN", style_title)],
        [Paragraph(f"ID: {orden_id}", ParagraphStyle('h2', parent=styles['Normal'], fontSize=9, textColor=COLOR_GRIS_OSCURO, alignment=TA_LEFT))]
    ]
    t_header = Table(header_data, colWidths=[7.5*inch])
    t_header.setStyle(TableStyle([
        ('LEFTPADDING', (0,0), (-1,-1), 0), 
        ('BOTTOMPADDING', (0,0), (-1,-1), 0),
        ('TOPPADDING', (0,0), (-1,-1), 0)
    ]))
    elements.append(t_header)
    elements.append(Spacer(1, 4))
    
    # ===== INFORMACIÓN GENERAL (DISEÑO APROBADO) =====
    
    # Estilos para labels y values
    style_label = ParagraphStyle(
        'label', 
        parent=styles['Normal'], 
        fontSize=7, 
        textColor=COLOR_COBRE, 
        fontName='Helvetica-Bold', 
        leading=8
    )
    
    style_value = ParagraphStyle(
        'value', 
        parent=styles['Normal'], 
        fontSize=7, 
        textColor=COLOR_GRIS_OSCURO, 
        leading=8
    )
    
    # 🎯 Estilos para el bloque de GALONES (derecha)
    style_g_title = ParagraphStyle(
        'galones_title', 
        parent=styles['Normal'], 
        fontSize=8, 
        textColor=COLOR_GRIS_OSCURO, 
        alignment=TA_CENTER, 
        fontName='Helvetica'
    )
    
    style_g_num = ParagraphStyle(
        'galones_number', 
        parent=styles['Normal'], 
        fontSize=32,
        textColor=COLOR_GRIS_OSCURO, 
        alignment=TA_CENTER, 
        fontName='Helvetica-Bold', 
        leading=32,
    )
    
    style_g_unit = ParagraphStyle(
        'galones_unit', 
        parent=styles['Normal'], 
        fontSize=10, 
        textColor=COLOR_COBRE, 
        alignment=TA_CENTER, 
        fontName='Helvetica-Bold'
    )
    
    # 🎯 Contenido del bloque de galones (3 líneas)
    content_galones = [
        Paragraph("TOTAL A PRODUCIR", style_g_title),
        Paragraph(str(int(galones_objetivo)), style_g_num),
        Paragraph("GALONES", style_g_unit)
    ]
    
    # 📋 Datos de la tabla (6 filas - MARCA, TIPO, COLOR en negrita)
    info_data = [
        # Fila 0: Span inicia aquí
        [
            Paragraph("Fórmula:", style_label), 
            Paragraph(formula_info.get("Formula_Key", "N/A"), style_value), 
            content_galones
        ],
        # Fila 1
        [
            Paragraph("Marca:", style_label),   
            Paragraph(f"<b>{formula_info.get('Marca', 'N/A')}</b>", style_value), 
            ''
        ],
        # Fila 2
        [
            Paragraph("Tipo:", style_label),    
            Paragraph(f"<b>{formula_info.get('Tipo', 'N/A')}</b>", style_value), 
            ''
        ],
        # Fila 3
        [
            Paragraph("Color:", style_label),   
            Paragraph(f"<b>{formula_info.get('Color', 'N/A')}</b>", style_value), 
            ''
        ],
        # Fila 4
        [
            Paragraph("Batch:", style_label),   
            Paragraph(batch_id or "—", style_value), 
            ''
        ],
        # Fila 5
        [
            Paragraph("PED:", style_label),     
            Paragraph(ped_id or "—", style_value), 
            ''
        ]
    ]
    
    # 📐 Dimensiones: Col 0 (Labels) | Col 1 (Values) | Col 2 (Galones)
    info_table = Table(info_data, colWidths=[0.8*inch, 4.2*inch, 2.5*inch])
    
    info_table.setStyle(TableStyle([
        # --- ALINEACIÓN GENERAL ---
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        
        # --- 🎯 FUSIÓN (SPAN) - Galones ocupa 6 filas ---
        ('SPAN', (2,0), (2,5)),  # Columna 2, desde fila 0 hasta fila 5
        ('ALIGN', (2,0), (2,5), 'CENTER'), 
        ('VALIGN', (2,0), (2,5), 'MIDDLE'), 
        
        # --- ESTÉTICA (compacto) ---
        ('LINEBEFORE', (2,0), (2,5), 1, COLOR_GRIS_CLARO),
        ('LEFTPADDING', (2,0), (2,5), 12),
        ('TOPPADDING', (0,0), (-1,-1), 1),
        ('BOTTOMPADDING', (0,0), (-1,-1), 1),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.04*inch))
    
    # ===== TABLA DE INGREDIENTES (toda la fórmula en una hoja, sin truncar) =====
    elements.append(Paragraph("<b>INGREDIENTES A PESAR</b>", style_subtitle))
    
    table_data = []
    table_data.append(["Código", "Nombre", "KG/PRO", "GL/PRO"])
    
    etapa_actual = None
    # Construir TODOS los ingredientes; marcar filas de etapa con "__ETAPA__nombre"
    for idx, row in df_escalado.iterrows():
        etapa = row.get("etapa", row.get("Etapa", "—"))
        if etapa != etapa_actual:
            table_data.append([f"__ETAPA__{etapa}", "", "", ""])
            etapa_actual = etapa
        
        codigo = row.get("CODIGO", "—")
        nombre = row.get("nombre", "—")
        kg_pro = f"{row.get('KG_PRO', 0):.2f}"
        gl_pro = f"{row.get('GL_PRO', 0):.2f}"
        if len(nombre) > 40:
            nombre = nombre[:37] + "..."
        table_data.append([codigo, nombre, kg_pro, gl_pro])
    
    total_kg = df_escalado["KG_PRO"].sum()
    total_gl = df_escalado["GL_PRO"].sum()
    table_data.append(["", "TOTAL", f"{total_kg:.2f}", f"{total_gl:.2f}"])
    
    # Escalado inteligente: fuente y padding según número de filas
    n_rows = len(table_data)
    layout = _compute_table_layout(n_rows)
    fs_h = layout["fontSize_header"]
    fs_c = layout["fontSize_codigo"]
    fs_n = layout["fontSize_nombre"]
    fs_num = layout["fontSize_nums"]
    fs_etapa = layout["fontSize_etapa"]
    pad = layout["padding_pt"]
    
    # Reemplazar placeholders __ETAPA__nombre por Paragraphs con fuente escalada
    for i in range(1, len(table_data) - 1):
        cell = table_data[i][0]
        if isinstance(cell, str) and cell.startswith("__ETAPA__"):
            etapa_nombre = cell.replace("__ETAPA__", "", 1)
            etapa_para = Paragraph(
                f"<b>{etapa_nombre.upper()}</b>",
                ParagraphStyle(
                    'EtapaSeparator',
                    fontSize=fs_etapa,
                    leading=fs_etapa + 1,
                    textColor=colors.white,
                    fontName='Helvetica-Bold',
                    alignment=TA_LEFT
                )
            )
            table_data[i][0] = etapa_para
    
    ingredients_table = Table(
        table_data,
        colWidths=[0.7*inch, 4.0*inch, 1.0*inch, 1.0*inch],
        repeatRows=1
    )
    
    base_styles = [
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_COBRE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), fs_h),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_GRIS_OSCURO),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), fs_h),
        ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
        ('LEFTPADDING', (0, 0), (-1, -1), pad),
        ('RIGHTPADDING', (0, 0), (-1, -1), pad),
        ('TOPPADDING', (0, 0), (-1, -1), pad),
        ('BOTTOMPADDING', (0, 0), (-1, -1), pad),
    ]
    
    etapa_styles = []
    ingredient_rows = []
    for i, row in enumerate(table_data[1:-1], start=1):
        # Filas de etapa: nombre vacío y celdas numéricas vacías
        is_etapa = (row[1] == "" and row[2] == "" and row[3] == "")
        if is_etapa:
            etapa_styles.append(('SPAN', (0, i), (-1, i)))
            etapa_styles.append(('BACKGROUND', (0, i), (-1, i), COLOR_GRIS_OSCURO))
            etapa_styles.append(('TEXTCOLOR', (0, i), (-1, i), colors.white))
            etapa_styles.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
            etapa_styles.append(('FONTSIZE', (0, i), (-1, i), fs_etapa))
            etapa_styles.append(('ALIGN', (0, i), (-1, i), 'LEFT'))
            etapa_styles.append(('VALIGN', (0, i), (-1, i), 'MIDDLE'))
            etapa_styles.append(('TOPPADDING', (0, i), (-1, i), pad))
            etapa_styles.append(('BOTTOMPADDING', (0, i), (-1, i), pad))
            etapa_styles.append(('LEFTPADDING', (0, i), (-1, i), pad + 2))
        else:
            ingredient_rows.append(i)
    
    if ingredient_rows:
        ingredient_styles = [
            ('FONTSIZE', (0, ingredient_rows[0]), (0, ingredient_rows[-1]), fs_c),
            ('FONTSIZE', (1, ingredient_rows[0]), (1, ingredient_rows[-1]), fs_n),
            ('FONTSIZE', (2, ingredient_rows[0]), (2, ingredient_rows[-1]), fs_num),
            ('FONTSIZE', (3, ingredient_rows[0]), (3, ingredient_rows[-1]), fs_num),
            ('FONTNAME', (0, ingredient_rows[0]), (0, ingredient_rows[-1]), 'Helvetica'),
            ('FONTNAME', (1, ingredient_rows[0]), (1, ingredient_rows[-1]), 'Helvetica-Bold'),
            ('FONTNAME', (2, ingredient_rows[0]), (3, ingredient_rows[-1]), 'Helvetica-Bold'),
            ('ALIGN', (0, ingredient_rows[0]), (0, ingredient_rows[-1]), 'CENTER'),
            ('ALIGN', (1, ingredient_rows[0]), (1, ingredient_rows[-1]), 'LEFT'),
            ('ALIGN', (2, ingredient_rows[0]), (-1, ingredient_rows[-1]), 'RIGHT'),
            ('VALIGN', (0, ingredient_rows[0]), (-1, ingredient_rows[-1]), 'MIDDLE'),
        ]
        for i, row_idx in enumerate(ingredient_rows):
            if i % 2 == 0:
                ingredient_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), colors.white))
            else:
                ingredient_styles.append(('BACKGROUND', (0, row_idx), (-1, row_idx), COLOR_FONDO))
    else:
        ingredient_styles = []
    
    ingredients_table.setStyle(TableStyle(base_styles + etapa_styles + ingredient_styles))
    
    elements.append(ingredients_table)
    elements.append(Spacer(1, 0.02*inch))
    
    # ===== OBSERVACIONES =====
    if observaciones:
        if len(observaciones) > 100:
            observaciones = observaciones[:97] + "..."
        elements.append(Paragraph(f"<b>Obs:</b> {observaciones}", style_normal))
        elements.append(Spacer(1, 0.01*inch))
    
    # ===== FIRMA (compacta) =====
    firma_data = [["Operario: ___________________", "Fecha: ___________________"]]
    firma_table = Table(
        firma_data, 
        colWidths=[3.75*inch, 3.75*inch],
        rowHeights=[0.2*inch],
    )
    firma_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(firma_table)
    elements.append(Spacer(1, 0.01*inch))
    
    # ===== FOOTER =====
    fecha_gen = datetime.now().strftime("%Y-%m-%d %H:%M")
    footer = Paragraph(
        f"<i>Generado: {fecha_gen} | Sistema Formulab v1.0 | GREQ</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=6, textColor=COLOR_GRIS_MEDIO, alignment=TA_CENTER)
    )
    elements.append(footer)
    
    # ===== GENERAR PDF =====
    doc.build(elements)
    
    return output_path
