"""
PDF Generator para Órdenes de Producción - GREQ
------------------------------------------------
Versión: 3.1 (Sistema unificado – expandir/contraer todo junto)
Cambios en v3.1:
- ✅ Un solo factor (block_scale): header, info, tabla, spacers y firma escalan juntos
- ✅ Padding mínimo en celdas (4 pt) para que el texto no solape los bordes
- ✅ Número "Total a producir" fijo en 42 pt (no se reduce)
- ✅ Marca, Tipo y Color con estilo más grande (value_bold, escala con s)
- ✅ Referencia 22 filas: más items → todo más compacto; menos items → todo más amplio

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
FONT_MIN, FONT_MAX = 5, 12
# Padding mínimo en celdas para que el texto no solape los bordes
PAD_CELL_MIN_PT = 4
# Referencia de filas para el factor de escala (arriba de esto = contraer, abajo = expandir)
REF_ROWS = 22
BLOCK_SCALE_MIN, BLOCK_SCALE_MAX = 0.72, 1.15


def _count_table_rows(df_escalado) -> int:
    """Cuenta filas totales de la tabla: cabecera + etapas + ingredientes + total."""
    n = 1  # cabecera
    etapa_actual = None
    for _, row in df_escalado.iterrows():
        etapa = row.get("etapa", row.get("Etapa", "—"))
        if etapa != etapa_actual:
            n += 1
            etapa_actual = etapa
        n += 1
    return n + 1  # + fila TOTAL


def _compute_table_layout(n_rows: int):
    """
    Calcula fuente y padding de la tabla de ingredientes para una hoja.
    Padding mínimo PAD_CELL_MIN_PT para que el texto no toque los bordes.
    """
    if n_rows <= 0:
        n_rows = 1
    height_per_row_pt = AVAILABLE_TABLE_PT / n_rows
    # Padding: mínimo 4 pt para que no solape; máximo ~30% de la fila
    pad = max(PAD_CELL_MIN_PT, int(height_per_row_pt * 0.15))
    pad = min(pad, max(PAD_CELL_MIN_PT, int(height_per_row_pt * 0.35)))
    # Fuente: lo que quepa con ese padding (leading ≈ 1.2 * fontSize)
    font_calc = (height_per_row_pt - 2 * pad) / 1.2
    font_clamped = max(FONT_MIN, min(FONT_MAX, int(math.floor(font_calc))))
    if font_clamped < FONT_MIN and pad > PAD_CELL_MIN_PT:
        pad = max(PAD_CELL_MIN_PT, int((height_per_row_pt - FONT_MIN * 1.2) / 2))
        font_clamped = FONT_MIN
    return {
        "fontSize_header": font_clamped,
        "fontSize_codigo": max(FONT_MIN, font_clamped - 1),
        "fontSize_nombre": font_clamped,
        "fontSize_nums": min(FONT_MAX, font_clamped + 1),
        "fontSize_etapa": font_clamped,
        "padding_pt": max(PAD_CELL_MIN_PT, pad),
    }


def _format_galones_display(galones: float) -> str:
    """Formato legible para el bloque 'Total a producir': enteros sin decimales, muestras con decimales."""
    if galones >= 100 or (galones >= 1 and galones == round(galones, 0)):
        return str(int(round(galones, 0)))
    # Muestras de laboratorio o valores con decimales: mostrar hasta 2 decimales, sin ceros finales
    return f"{galones:.2f}".rstrip("0").rstrip(".")


def _compute_block_scale(n_rows: int) -> float:
    """Factor único: todo el bloque (header, info, spacers) se expande o contrae junto."""
    scale = REF_ROWS / max(1, n_rows)
    return max(BLOCK_SCALE_MIN, min(BLOCK_SCALE_MAX, scale))

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
    
    # ----- Sistema unificado: precalcular n_rows y escalas -----
    n_table_rows = _count_table_rows(df_escalado)
    layout = _compute_table_layout(n_table_rows)
    block_scale = _compute_block_scale(n_table_rows)
    # Escala aplicada a todo el bloque superior (header, info, spacers, firma)
    s = block_scale
    
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
    
    # Estilos que escalan con block_scale (todo se expande o contrae junto)
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=max(8, int(12 * s)),
        textColor=COLOR_COBRE,
        spaceAfter=max(1, int(3 * s)),
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
    )
    
    style_subtitle = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=max(6, int(9 * s)),
        textColor=COLOR_GRIS_OSCURO,
        spaceAfter=max(1, int(3 * s)),
        alignment=TA_LEFT,
        fontName='Helvetica-Bold',
    )
    
    style_normal = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=max(5, int(7 * s)),
        spaceAfter=2,
        textColor=COLOR_GRIS_OSCURO,
    )
    
    style_label = ParagraphStyle(
        'label',
        parent=styles['Normal'],
        fontSize=max(6, int(7 * s)),
        textColor=COLOR_COBRE,
        fontName='Helvetica-Bold',
        leading=max(7, int(9 * s)),
    )
    
    style_value = ParagraphStyle(
        'value',
        parent=styles['Normal'],
        fontSize=max(6, int(7 * s)),
        textColor=COLOR_GRIS_OSCURO,
        leading=max(7, int(9 * s)),
    )
    
    # Marca, Tipo, Color: más grandes y en negrita (escalan con s)
    style_value_bold = ParagraphStyle(
        'value_bold',
        parent=styles['Normal'],
        fontSize=max(8, int(11 * s)),
        textColor=COLOR_GRIS_OSCURO,
        fontName='Helvetica-Bold',
        leading=max(9, int(13 * s)),
    )
    
    # Galones: número grande FIJO (no se reduce)
    style_g_title = ParagraphStyle(
        'galones_title',
        parent=styles['Normal'],
        fontSize=max(7, int(9 * s)),
        textColor=COLOR_GRIS_OSCURO,
        alignment=TA_CENTER,
        fontName='Helvetica',
    )
    
    style_g_num = ParagraphStyle(
        'galones_number',
        parent=styles['Normal'],
        fontSize=42,
        textColor=COLOR_GRIS_OSCURO,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
        leading=42,
    )
    
    style_g_unit = ParagraphStyle(
        'galones_unit',
        parent=styles['Normal'],
        fontSize=max(9, int(11 * s)),
        textColor=COLOR_COBRE,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold',
    )
    
    content_galones = [
        Paragraph("TOTAL A PRODUCIR", style_g_title),
        Paragraph(_format_galones_display(galones_objetivo), style_g_num),
        Paragraph("GALONES", style_g_unit),
    ]
    
    # Tabla info: Fórmula/otros con style_value; Marca, Tipo, Color con style_value_bold
    info_data = [
        [
            Paragraph("Fórmula:", style_label),
            Paragraph(formula_info.get("Formula_Key", "N/A"), style_value),
            content_galones,
        ],
        [
            Paragraph("Marca:", style_label),
            Paragraph(formula_info.get("Marca", "N/A") or "N/A", style_value_bold),
            "",
        ],
        [
            Paragraph("Tipo:", style_label),
            Paragraph(formula_info.get("Tipo", "N/A") or "N/A", style_value_bold),
            "",
        ],
        [
            Paragraph("Color:", style_label),
            Paragraph(formula_info.get("Color", "N/A") or "N/A", style_value_bold),
            "",
        ],
        [
            Paragraph("Batch:", style_label),
            Paragraph(batch_id or "—", style_value),
            "",
        ],
        [
            Paragraph("PED:", style_label),
            Paragraph(ped_id or "—", style_value),
            "",
        ],
    ]
    
    pad_info = max(1, int(3 * s))
    info_table = Table(info_data, colWidths=[0.8*inch, 4.2*inch, 2.5*inch])
    info_table.setStyle(TableStyle([
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('LEFTPADDING', (0,0), (-1,-1), 0),
        ('RIGHTPADDING', (0,0), (-1,-1), 0),
        ('SPAN', (2,0), (2,5)),
        ('ALIGN', (2,0), (2,5), 'CENTER'),
        ('VALIGN', (2,0), (2,5), 'MIDDLE'),
        ('LINEBEFORE', (2,0), (2,5), 1, COLOR_GRIS_CLARO),
        ('LEFTPADDING', (2,0), (2,5), max(8, int(14 * s))),
        ('TOPPADDING', (0,0), (-1,-1), pad_info),
        ('BOTTOMPADDING', (0,0), (-1,-1), pad_info),
    ]))
    
    elements.append(Paragraph("ORDEN DE PRODUCCIÓN", style_title))
    elements.append(Paragraph(
        f"ID: {orden_id}",
        ParagraphStyle('h2', parent=styles['Normal'], fontSize=max(7, int(9 * s)), textColor=COLOR_GRIS_OSCURO, alignment=TA_LEFT),
    ))
    elements.append(Spacer(1, max(2, int(6 * s))))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.04 * s * inch))
    
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
    
    # Usar layout ya calculado al inicio (n_table_rows == len(table_data))
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
    elements.append(Spacer(1, 0.02 * s * inch))
    
    # ===== OBSERVACIONES =====
    if observaciones:
        if len(observaciones) > 100:
            observaciones = observaciones[:97] + "..."
        elements.append(Paragraph(f"<b>Obs:</b> {observaciones}", style_normal))
        elements.append(Spacer(1, 0.01 * s * inch))
    
    # ===== FIRMA (escala con s) =====
    firma_fs = max(5, int(7 * s))
    firma_h = max(0.15, 0.22 * s) * inch
    firma_data = [["Operario: ___________________", "Fecha: ___________________"]]
    firma_table = Table(
        firma_data,
        colWidths=[3.75*inch, 3.75*inch],
        rowHeights=[firma_h],
    )
    firma_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), firma_fs),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(firma_table)
    elements.append(Spacer(1, 0.01 * s * inch))
    
    # ===== FOOTER (escala con s) =====
    fecha_gen = datetime.now().strftime("%Y-%m-%d %H:%M")
    footer_fs = max(5, int(6 * s))
    footer = Paragraph(
        f"<i>Generado: {fecha_gen} | Sistema Formulab v1.0 | GREQ</i>",
        ParagraphStyle('Footer', parent=styles['Normal'], fontSize=footer_fs, textColor=COLOR_GRIS_MEDIO, alignment=TA_CENTER),
    )
    elements.append(footer)
    
    # ===== GENERAR PDF =====
    doc.build(elements)
    
    return output_path
