"""
PDF Generator para Órdenes de Producción - GREQ
------------------------------------------------
Versión: 2.5 (Galones Destacados con Diseño Aprobado)
Cambios en v2.5:
- ✅ Galones en columna derecha con SPAN (diseño aprobado)
- ✅ Número grande 42pt + título + unidad
- ✅ Marca, Tipo, Color en negrita
- ✅ P/G eliminado (espacio optimizado)
- ✅ Borde gris claro separador
- ✅ Layout compacto 3 columnas

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
import os

# 🎨 Paleta de colores GREQ oficial
COLOR_COBRE = colors.HexColor("#B65A2A")
COLOR_GRIS_OSCURO = colors.HexColor("#3B3B3B")
COLOR_GRIS_MEDIO = colors.HexColor("#6E6E6E")
COLOR_GRIS_CLARO = colors.HexColor("#F0F0F0")
COLOR_FONDO = colors.HexColor("#F6F6F6")

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
    
    # 📐 LÍMITE MÁS AGRESIVO para garantizar espacio para firma
    MAX_FILAS_TABLA = 35
    
    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.5*inch,
        leftMargin=0.5*inch,
        topMargin=0.5*inch,
        bottomMargin=0.5*inch
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    style_title = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=14,
        textColor=COLOR_COBRE,
        spaceAfter=3,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
    )
    
    style_subtitle = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Heading2'],
        fontSize=9,
        textColor=COLOR_GRIS_OSCURO,
        spaceAfter=4,
        alignment=TA_LEFT,
        fontName='Helvetica-Bold'
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
    elements.append(Spacer(1, 10))
    
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
        fontSize=42,  # ✨ GRANDE
        textColor=COLOR_GRIS_OSCURO, 
        alignment=TA_CENTER, 
        fontName='Helvetica-Bold', 
        leading=42
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
        
        # --- ESTÉTICA ---
        ('LINEBEFORE', (2,0), (2,5), 1, COLOR_GRIS_CLARO),  # Borde separador
        ('LEFTPADDING', (2,0), (2,5), 20),  # Padding interno del bloque
        ('TOPPADDING', (0,0), (-1,-1), 2),
        ('BOTTOMPADDING', (0,0), (-1,-1), 2),
    ]))
    
    elements.append(info_table)
    elements.append(Spacer(1, 0.1*inch))
    
    # ===== TABLA DE INGREDIENTES =====
    elements.append(Paragraph("<b>INGREDIENTES A PESAR</b>", style_subtitle))
    
    table_data = []
    table_data.append(["Código", "Nombre", "KG/PRO", "GL/PRO"])
    
    etapa_actual = None
    filas_totales = 1
    ingredientes_omitidos = 0
    
    for idx, row in df_escalado.iterrows():
        etapa = row.get("etapa", row.get("Etapa", "—"))
        
        nueva_etapa = (etapa != etapa_actual)
        filas_necesarias = 2 if nueva_etapa else 1
        
        # 🛑 LÍMITE ESTRICTO
        if filas_totales + filas_necesarias + 1 > MAX_FILAS_TABLA:
            ingredientes_omitidos = len(df_escalado) - idx
            break
        
        if nueva_etapa:
            etapa_para = Paragraph(
                f"<b>{etapa.upper()}</b>",
                ParagraphStyle(
                    'EtapaSeparator',
                    fontSize=7,
                    leading=8,
                    textColor=colors.white,
                    fontName='Helvetica-Bold',
                    alignment=TA_LEFT
                )
            )
            table_data.append([etapa_para, "", "", ""])
            etapa_actual = etapa
            filas_totales += 1
        
        codigo = row.get("CODIGO", "—")
        nombre = row.get("nombre", "—")
        kg_pro = f"{row.get('KG_PRO', 0):.2f}"
        gl_pro = f"{row.get('GL_PRO', 0):.2f}"
        
        if len(nombre) > 35:
            nombre = nombre[:32] + "..."
        
        table_data.append([codigo, nombre, kg_pro, gl_pro])
        filas_totales += 1
    
    if ingredientes_omitidos > 0:
        table_data.append(["...", f"({ingredientes_omitidos} ingredientes adicionales)", "...", "..."])
        df_mostrado = df_escalado.iloc[:len(df_escalado) - ingredientes_omitidos]
        total_kg = df_mostrado["KG_PRO"].sum()
        total_gl = df_mostrado["GL_PRO"].sum()
        nota_total = "SUBTOTAL*"
    else:
        total_kg = df_escalado["KG_PRO"].sum()
        total_gl = df_escalado["GL_PRO"].sum()
        nota_total = "TOTAL"
    
    table_data.append(["", nota_total, f"{total_kg:.2f}", f"{total_gl:.2f}"])
    
    ingredients_table = Table(
        table_data,
        colWidths=[0.7*inch, 4.0*inch, 1.0*inch, 1.0*inch],
        repeatRows=1
    )
    
    # ESTILOS BASE CON PADDING MÍNIMO
    base_styles = [
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), COLOR_COBRE),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 7),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Total
        ('BACKGROUND', (0, -1), (-1, -1), COLOR_GRIS_OSCURO),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 7),
        ('ALIGN', (0, -1), (-1, -1), 'RIGHT'),
        
        ('GRID', (0, 0), (-1, -1), 0.5, COLOR_GRIS_MEDIO),
        
        # PADDING ULTRA-COMPACTO
        ('LEFTPADDING', (0, 0), (-1, -1), 2),
        ('RIGHTPADDING', (0, 0), (-1, -1), 2),
        ('TOPPADDING', (0, 0), (-1, -1), 1),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 1),
    ]
    
    etapa_styles = []
    ingredient_rows = []
    
    for i, row in enumerate(table_data[1:-1], start=1):
        if row[1] == "" and row[2] == "" and row[3] == "":
            etapa_styles.append(('SPAN', (0, i), (-1, i)))
            etapa_styles.append(('BACKGROUND', (0, i), (-1, i), COLOR_GRIS_OSCURO))
            etapa_styles.append(('TEXTCOLOR', (0, i), (-1, i), colors.white))
            etapa_styles.append(('FONTNAME', (0, i), (-1, i), 'Helvetica-Bold'))
            etapa_styles.append(('FONTSIZE', (0, i), (-1, i), 7))
            etapa_styles.append(('ALIGN', (0, i), (-1, i), 'LEFT'))
            etapa_styles.append(('VALIGN', (0, i), (-1, i), 'MIDDLE'))
            etapa_styles.append(('TOPPADDING', (0, i), (-1, i), 2))
            etapa_styles.append(('BOTTOMPADDING', (0, i), (-1, i), 2))
            etapa_styles.append(('LEFTPADDING', (0, i), (-1, i), 4))
        else:
            ingredient_rows.append(i)
    
    if ingredient_rows:
        ingredient_styles = [
            # Tamaños por columna
            ('FONTSIZE', (0, ingredient_rows[0]), (0, ingredient_rows[-1]), 6),   # Código
            ('FONTSIZE', (1, ingredient_rows[0]), (1, ingredient_rows[-1]), 7),   # Nombre
            ('FONTSIZE', (2, ingredient_rows[0]), (2, ingredient_rows[-1]), 8),   # KG
            ('FONTSIZE', (3, ingredient_rows[0]), (3, ingredient_rows[-1]), 8),   # GL
            
            # Bold
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
    
    if ingredientes_omitidos > 0:
        nota_truncado = Paragraph(
            f"<i>*Mostrando primeros {len(df_escalado) - ingredientes_omitidos} de {len(df_escalado)} ingredientes</i>",
            ParagraphStyle('NotaTruncado', fontSize=6, textColor=COLOR_GRIS_MEDIO)
        )
        elements.append(nota_truncado)
        elements.append(Spacer(1, 0.02*inch))
    else:
        elements.append(Spacer(1, 0.03*inch))
    
    # ===== OBSERVACIONES (ultra-compactas) =====
    if observaciones:
        if len(observaciones) > 100:
            observaciones = observaciones[:97] + "..."
        elements.append(Paragraph(f"<b>Obs:</b> {observaciones}", style_normal))
        elements.append(Spacer(1, 0.02*inch))
    
    # ===== FIRMA (ULTRA-COMPACTA CON ALTURA FIJA) =====
    firma_data = [["Operario: ___________________", "Fecha: ___________________"]]
    firma_table = Table(
        firma_data, 
        colWidths=[3.75*inch, 3.75*inch],
        rowHeights=[0.25*inch]
    )
    firma_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 7),
        ('LEFTPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    
    elements.append(firma_table)
    elements.append(Spacer(1, 0.02*inch))
    
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
