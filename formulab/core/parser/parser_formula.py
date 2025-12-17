# -*- coding: utf-8 -*-
"""
Parser robusto para fórmulas de pintura (MILAN / INFINITI) - v2.4
- Sin normalización de CANT (no maquillar; solo reportar)
- Validaciones físicas: (1) sum(KG)/sum(GL) ≈ P/G, (2) sum(GL/PRO) ≈ gal_producir
- Split inteligente y detección de etapas con fuzzy matching
- Filtros de headers corregidos (no excluir nombres químicos por 'DI', 'OA', etc.)
"""

import re
import pandas as pd
from difflib import SequenceMatcher

# ==================== HELPERS ====================

def to_float(s):
    """Convierte string a float, manejando formatos inconsistentes."""
    if s is None:
        return None
    x = str(s).strip()
    if not x:
        return None
    x = x.replace("\u00A0", "").replace(" ", "")
    x = x.replace("$", "").replace("%", "")
    # Decimal con coma europea
    if x.count(",") == 1 and x.count(".") == 0:
        x = x.replace(",", ".")
    # Separador de miles tipo 1.234.567 -> 1234567
    if x.count(".") > 1 and "," not in x:
        *ints, dec = x.split(".")
        x = "".join(ints) + "." + dec
    try:
        return float(x)
    except:
        return None


def clean_spaces(s):
    return re.sub(r"\s+", " ", s or "").strip()


def split_loose_v2(line):
    """
    Split inteligente con 4 estrategias en cascada:
    1) Tabs
    2) Espacios 4+
    3) Espacios 2+
    4) Split 'smart' por códigos/números/unidades
    """
    if "\t" in line:
        parts = [p.strip() for p in line.split("\t") if p.strip()]
        return parts

    parts = re.split(r"\s{4,}", line.strip())
    if len(parts) > 3:
        return [p.strip() for p in parts if p.strip()]

    parts = re.split(r"\s{2,}", line.strip())
    if len(parts) > 3:
        return [p.strip() for p in parts if p.strip()]

    tokens, buffer = [], []
    words = line.split()
    for word in words:
        if re.match(r"^[A-Z]{2,3}-\d{3,5}$", word):  # Código (SV-0001 / PE-010 / etc.)
            if buffer:
                tokens.append(" ".join(buffer)); buffer = []
            tokens.append(word)
        elif re.match(r"^\d+[\.,]\d+$", word):       # Número decimal
            if buffer:
                tokens.append(" ".join(buffer)); buffer = []
            tokens.append(word)
        elif word.upper() in {"KG", "GL", "LB", "G", "L"}:
            if buffer:
                tokens.append(" ".join(buffer)); buffer = []
            tokens.append(word)
        else:
            buffer.append(word)
    if buffer:
        tokens.append(" ".join(buffer))
    return tokens


# ==================== ETAPAS (FUZZY) ====================

# ✅ DESPUÉS (con tiempos incluidos)
ETAPAS_CONOCIDAS = {
    "Mezcla rápida (2–3 min)": ["MEZCLAR", "MELANGER", "MIXING", "MIX", "MEZCLA"],
    "Dispersión Cowles (15 min @ 1600–2800 RPM)": ["DISPERSAR", "COWLES", "DISPERS", "DISPERSE"],
    "Disolución lenta (5–10 min)": ["DISOLVER", "DISOL", "DISSOLVE", "DISSOLUTION"]
}

def fuzzy_match_stage(text, threshold=0.65):
    text_upper = text.upper()
    best_match, best_score = None, 0.0
    for stage_name, keywords in ETAPAS_CONOCIDAS.items():
        for kw in keywords:
            if kw in text_upper:
                return stage_name
            ratio = SequenceMatcher(None, text_upper, kw).ratio()
            if ratio > best_score and ratio >= threshold:
                best_score, best_match = ratio, stage_name
    return best_match


def stage_from_line(ln, current_stage):
    matched = fuzzy_match_stage(ln)
    if matched:
        return matched
    U = ln.upper()
    if "MEZCLAR" in U or "MELANGER" in U or "MIX" in U:
        # Ya no distinguir entre inicial/final aquí
        return "Mezcla rápida (2–3 min)"
    if "DISPERSAR" in U or "COWLES" in U:
        return "Dispersión Cowles (15 min @ 1600–2800 RPM)"
    if "DISOL" in U or "DISSOLV" in U:
        return "Disolución lenta (5–10 min)"
    return current_stage

def _pick_int_candidates(lines, start=0, end=12):
    """
    Busca enteros 'desnudos' en las primeras N líneas: ej. '200' en una celda sola.
    Regresa una lista de candidatos (int) encontrados en [start, end).
    """
    cands = []
    hi = min(len(lines), end if end is not None else len(lines))
    for i in range(start, hi):
        ln = lines[i].strip()
        # Línea que es SOLAMENTE un entero (sin signos, sin decimales)
        if re.fullmatch(r"\d{2,5}", ln):  # ej. 25 .. 99999 (ajusta si quieres)
            val = int(ln)
            # Rango razonable de lotes (puedes ajustar)
            if 10 <= val <= 5000:
                cands.append(val)
    return cands

def _find_after_anchor(lines, anchor_regex, lookahead=3):
    """
    Busca una línea ANCLA (regex) y, si la encuentra, mira en esa línea y las siguientes 'lookahead'
    una cifra entera aislada. Devuelve el primer match (int) o None.
    """
    for idx, ln in enumerate(lines):
        if re.search(anchor_regex, ln, re.I):
            # 1) intentar en la MISMA línea
            same_line = re.findall(r"\b(\d{2,5})\b", ln)
            same_line = [int(x) for x in same_line if 10 <= int(x) <= 5000]
            if same_line:
                return same_line[0]
            # 2) intentar líneas siguientes (celdas solas típicas)
            for j in range(1, lookahead + 1):
                if idx + j < len(lines):
                    nxt = lines[idx + j].strip()
                    if re.fullmatch(r"\d{2,5}", nxt):
                        val = int(nxt)
                        if 10 <= val <= 5000:
                            return val
    return None

def detect_gal_producir(all_text, default_gals=250.0):
    """
    🆕 v2.6: Detección robusta de gal_producir
    
    Estrategia en orden de prioridad:
    1. Celda aislada con número decimal (0.1 - 5000.0)
       - En primeras 15 líneas
       - Formato: "	5" o "  0.75" (tab/espacios + número)
    
    2. Línea con prefijo conocido + número
       - "modificacion 1  0.75" → 0.75
       - "STANDARD  25" → 25
    
    3. Número aislado en primeras 15 líneas (sin prefijo)
       - "200" en celda sola
    
    4. Fallback: TOTAL → último número razonable
    
    5. Default: 250.0
    """
    lines = [ln for ln in all_text.splitlines() if ln.strip()]
    
    # ==================== PRIORIDAD 1: CELDA AISLADA ====================
    # Buscar en primeras 15 líneas (zona de metadata)
    for i in range(min(15, len(lines))):
        ln = lines[i]
        ln_stripped = ln.strip()
        
        # Skip headers conocidos
        if any(kw in ln_stripped.upper() for kw in [
            "VOLUMEN", "P/G", "COSTO", "FECHA", "GALONES PRODUCIDOS",
            "CODIGO", "NOMBRE", "CANT", "UNIDAD", "PRECIO"
        ]):
            continue
        
        # Detectar número aislado (celda sola)
        # Formato: línea que es SOLO espacios/tabs + número (puede tener decimales)
        match = re.fullmatch(r"[\s\t]*([0-9]+(?:[.,][0-9]+)?)[\s\t]*", ln)
        if match:
            val_str = match.group(1).replace(",", ".")
            try:
                val = float(val_str)
                # Rango razonable para galones (0.1 - 5000)
                if 0.1 <= val <= 5000.0:
                    return val
            except:
                pass
    
    # ==================== PRIORIDAD 2: PREFIJO + NÚMERO ====================
    # Buscar líneas con "modificacion", "STANDARD", etc.
    for i in range(min(15, len(lines))):
        ln = lines[i].strip()
        
        # Patrón: "modificacion [opcional] NÚMERO"
        match_mod = re.search(r"modificacion\s+\d*\s*([0-9]+(?:[.,][0-9]+)?)", ln, re.I)
        if match_mod:
            val_str = match_mod.group(1).replace(",", ".")
            try:
                val = float(val_str)
                if 0.1 <= val <= 5000.0:
                    return val
            except:
                pass
        
        # Patrón: "STANDARD NÚMERO"
        match_std = re.search(r"STANDARD\s+([0-9]+(?:[.,][0-9]+)?)", ln, re.I)
        if match_std:
            val_str = match_std.group(1).replace(",", ".")
            try:
                val = float(val_str)
                if 0.1 <= val <= 5000.0:
                    return val
            except:
                pass
    
    # ==================== PRIORIDAD 3: NÚMERO ENTERO AISLADO ====================
    # Buscar enteros grandes (>10) en primeras 15 líneas
    for i in range(min(15, len(lines))):
        ln = lines[i].strip()
        
        # Número solo en la línea (sin letras)
        if re.fullmatch(r"\d{2,5}", ln):
            val = int(ln)
            if 10 <= val <= 5000:
                return float(val)
    
    # ==================== PRIORIDAD 4: TOTAL (ÚLTIMAS LÍNEAS) ====================
    # Buscar en últimas 5 líneas por si el valor está en TOTAL
    tail = lines[max(0, len(lines)-5):]
    for ln in reversed(tail):
        # Extraer todos los números de la línea
        nums = re.findall(r"[0-9]+(?:[.,][0-9]+)?", ln)
        
        for num_str in reversed(nums):  # De derecha a izquierda
            num_str_clean = num_str.replace(",", ".")
            try:
                val = float(num_str_clean)
                # Si es un número razonable como galones
                if 0.1 <= val <= 5000.0:
                    # Preferir números enteros o con pocos decimales
                    if abs(val - round(val)) < 0.01 or val < 10:
                        return val
            except:
                pass
    
    # ==================== FALLBACK ====================
    return default_gals


# ==================== EXTRACCIÓN METADATA ====================

def extract_metadata(all_text, default_gals=250.0):
    """
    🆕 v2.8: Fix para formatos con "VOLUMEN P/G" en header
    Extrae: tipo, color, Volumen, P/G, gal_producir
    """
    lines = [ln for ln in all_text.splitlines() if ln.strip()]
    joined = "\n".join(lines)

    # Tipo: primera línea visible, cortando "VOLUMEN" si aparece
    raw_tipo = lines[0] if lines else ""
    if "VOLUMEN" in raw_tipo.upper():
        raw_tipo = raw_tipo.upper().split("VOLUMEN")[0]
    tipo = re.sub(r"\s+", " ", raw_tipo).strip().title()

    color = None
    vol = None
    pg = None
    
    # 🔍 Buscar header "VOLUMEN P/G" en primeras 5 líneas
    header_idx = -1
    for idx in range(min(5, len(lines))):
        if re.search(r"\bVOLUMEN\b.*\bP\s*/\s*G\b", lines[idx].upper()):
            header_idx = idx
            break
    
    # Si encontramos header, parsear línea siguiente
    if header_idx >= 0 and header_idx + 1 < len(lines):
        data_line = lines[header_idx + 1]
        parts = split_loose_v2(data_line)
        
        # Extraer números (ignorando texto inicial del color)
        numbers = []
        color_text = []
        found_first_number = False
        
        for part in parts:
            num = to_float(part)
            if num is not None:
                found_first_number = True
                numbers.append(num)
            elif not found_first_number:
                # Antes del primer número = parte del color
                color_text.append(part)
        
        # Asignar valores
        if len(numbers) >= 2:
            vol = numbers[0]  # Primer número = Volumen
            pg = numbers[1]   # Segundo número = P/G
        
        if color_text:
            color = " ".join(color_text).strip().title()
    
    # Fallback: método original
    if vol is None or pg is None:
        for ln in lines[1:12]:
            if "CODIGO" in ln.upper():
                break
            m = re.match(r"^\s*(.*?)\s+([0-9\.,]+)\s+([0-9\.,]+)\b", ln)
            if m:
                cand_color = re.sub(r"\s+", " ", (m.group(1) or "")).strip()
                if not re.search(r"MODIFIC|COSTO|FECHA|PRODUCIDOS|P/?G|VOLUMEN|TOTAL", cand_color, re.I):
                    if color is None:
                        color = cand_color.title() if cand_color else None
                    if vol is None:
                        vol = to_float(m.group(2))
                    if pg is None:
                        pg = to_float(m.group(3))
                    break

    # Fallbacks adicionales
    if vol is None:
        m = re.search(r"\bVOLUMEN\b[^0-9]*([0-9\.,]+)", joined, re.I)
        if m: vol = to_float(m.group(1))
    if pg is None:
        m = re.search(r"\bP\s*/\s*G\b[^0-9]*([0-9\.,]+)", joined, re.I)
        if m: pg = to_float(m.group(1))

    # 🆕 gal_producir: Buscar en TOTAL (última línea con "TOTAL")
    gal = None
    for ln in reversed(lines):
        if "TOTAL" in ln.upper():
            # Extraer último número de 2+ dígitos (GL/PRO final)
            nums = re.findall(r"[0-9]+(?:[.,][0-9]+)?", ln)
            for n in reversed(nums):
                val = to_float(n)
                if val and 0.1 <= val <= 5000.0:
                    gal = val
                    break
            if gal:
                break
    
    # Si no hay TOTAL, usar detect_gal_producir (excluye "100" suelto)
    if gal is None:
        gal = detect_gal_producir(all_text, default_gals=default_gals)

    return {
        "tipo": tipo or None,
        "color": color or None,
        "Volumen": vol,
        "P/G": pg,
        "gal_producir": gal,
        "presentación": "STANDARD",
        "version": "1.0"
    }

# ==================== FORMULA KEY ====================

def build_formula_key(meta, brand_code=None, override_key=None):
    """
    Genera formula_key con marca desde Streamlit.
    
    Formato: <MARCA>-<TIPO_TAG>-<COLOR_TAG>
    
    Args:
        meta (dict): Debe incluir 'tipo', 'color', 'marca'
        brand_code (str): Override manual de prefijo
        override_key (str): Key completa manual
    
    Returns:
        str: Formula_Key generada
    """
    import re
    from formulab.sheets.tipo_mapeo_manager import buscar_tipo_tag, sugerir_tipo_tag
    
    if override_key:
        return override_key
    
    # 1. Buscar tipo en mapeo
    tipo_raw = meta.get("tipo", "")
    tipo_tag, encontrado = buscar_tipo_tag(tipo_raw)
    
    # 2. Alerta si no encontrado
    if not encontrado:
        print(f"\n⚠️ TIPO NUEVO DETECTADO: '{tipo_raw}'")
        print(f"   Tag generado: 'GEN'")
        print(f"   Tag sugerido: '{sugerir_tipo_tag(tipo_raw)}'")
        print(f"   Registrar: registrar_tipo_nuevo('{tipo_raw}', '<TAG>')\n")
    
    # 3. Determinar prefijo de marca
    if brand_code:
        # Override manual (prioridad máxima)
        brand_prefix = brand_code
    elif "marca" in meta and meta["marca"]:
        # Desde Streamlit (radio button)
        marca_meta = meta["marca"].upper()
        brand_prefix = "IN" if marca_meta == "INFINITI" else "PM"
    else:
        # Fallback por defecto
        brand_prefix = "IN"
    
    # 4. Color tag
    col_raw = (meta.get("color") or "").upper()
    col_clean = re.sub(r"[^A-Z0-9\-]", "", col_raw)
    color_tag = col_clean or "BL"
    
    return f"{brand_prefix}-{tipo_tag}-{color_tag}"
# ==================== PARSEO DE INGREDIENTES ====================

CODE_PAT = re.compile(r"^[A-Z]{2,3}-\d{3,5}\b")

CODE_PAT = re.compile(r"^[A-Z]{2,3}-\d{3,5}\b")

def parse_rows(all_text):
    """
    v3.0: Two-pass processing para asignación correcta de etapas
    
    PASS 1: Extraer ingredientes (sin etapa)
    PASS 2: Detectar headers y asignar etapas retrospectivamente
    """
    lines = [ln for ln in all_text.splitlines() if ln.strip()]
    
    # ========== PASS 1: EXTRAER INGREDIENTES ==========
    ingredientes = []  # Lista de (line_idx, ingrediente_dict)
    has_codes = any(CODE_PAT.match(ln.strip()) for ln in lines[:15])
    
    header_found, header_line_idx = False, -1
    for i, ln in enumerate(lines[:15]):
        if re.search(r"\b(CODIGO|NOMBRE\s+GENERICO)\b", ln.upper()):
            header_found, header_line_idx = True, i
            break
    
    tail_threshold = int(len(lines) * 0.9)
    
    for idx, ln in enumerate(lines):
        ln_stripped = ln.strip()
        if not ln_stripped:
            continue
        
        U = ln_stripped.upper()
        
        # Skips (headers, metadata, etc.)
        if re.search(r"\b(CODIGO|NOMBRE\s+GENERICO|TOTAL|PRECIO\s+US\$|VOLUMEN|P/\s?G|COSTO|FECHA|GALONES\s+PRODUCIDOS)\b", U):
            continue
        
        if idx < 2 and re.search(r"\b(ACRILICA|INFINITI|MILAN|SEMIGLOSS|SUPERIOR|PROYECTO|PORT|EPOXI)\b", U):
            continue
        
        if not header_found or (header_found and idx < header_line_idx):
            probe = split_loose_v2(ln)
            if len(probe) >= 2:
                first_num = to_float(probe[1])
                if first_num and first_num > 10.0:
                    continue
        
        if re.search(r"\b(STANDARD|MODIFICACION\s+CON\s+OP)\b", U):
            continue
        
        # Detección de TOTAL
        parts_check = split_loose_v2(ln)
        if len(parts_check) > 0:
            first_token_num = to_float(parts_check[0])
            num_count = sum(1 for p in parts_check if to_float(p) is not None)
            
            if idx >= tail_threshold and first_token_num is not None:
                if 98.0 <= first_token_num <= 102.0 and num_count >= 8:
                    continue
        
        # Skip headers de etapas (se procesan en PASS 2)
        first_token = (ln_stripped.split()[0] if ln_stripped.split() else "")
        if not to_float(first_token) and not CODE_PAT.match(first_token):
            if re.search(r"(MEZCLAR|DISPERSAR|DISOL|COWLES|MELANGER|MINUTOS|MINUTES|AJOUTER|CONTOLE)", U):
                continue  # Es un header, no ingrediente
        
        # ---- PARSEO DE INGREDIENTE ----
        parts = split_loose_v2(ln)
        if len(parts) < 3:
            continue
        
        codigo, nombre, numbers_start = None, None, 0
        
        if has_codes and CODE_PAT.match(parts[0]):
            codigo = parts[0].strip()
            nombre = parts[1].strip()
            numbers_start = 2
        else:
            if len(parts) < 2:
                continue
            
            second_val = to_float(parts[1])
            if second_val is None or second_val > 100.0:
                continue
            
            if re.search(r"\d{2,3}-\d{2}", parts[0]):
                continue
            
            if to_float(parts[0]) is not None:
                continue
            
            codigo = "SIN-CODIGO"
            nombre = parts[0].strip()
            numbers_start = 1
        
        if not nombre:
            continue
        
        num_tokens = [to_float(p) for p in parts[numbers_start:] if to_float(p) is not None]
        if len(num_tokens) < 2:
            continue
        
        cant = num_tokens[0]
        if cant is None or cant == 0 or cant < 0.001:
            continue
        
        kg = cant
        densidad = None
        gl = None
        
        for n in num_tokens[1:4]:
            if n is not None and 2.8 <= n <= 25.0:
                densidad = n
                break
        
        if densidad and kg:
            gl = round(kg / densidad, 2)
        
        kg_pro, gl_pro = None, None
        if len(num_tokens) >= 2:
            kg_pro, gl_pro = num_tokens[-2], num_tokens[-1]
        
        # Guardar ingrediente con su índice de línea
        ingredientes.append((idx, {
            "CODIGO": codigo,
            "Nombre": nombre,
            "CANT": cant,
            "UNIDAD": "KG",
            "Densidad (KG/GL)": densidad,
            "KG": kg,
            "GL": gl,
            "KG/PRO": kg_pro,
            "GL/PRO": gl_pro
        }))
    
    # ========== PASS 2: DETECTAR ETAPAS Y ASIGNAR ==========
    
    # Detectar headers de etapas con sus índices de línea
    etapa_headers = []  # Lista de (line_idx, etapa_nombre)
    
    for idx, ln in enumerate(lines):
        ln_stripped = ln.strip()
        U = ln_stripped.upper()
        
        # Verificar que NO sea un ingrediente
        first_token = (ln_stripped.split()[0] if ln_stripped.split() else "")
        if to_float(first_token) or CODE_PAT.match(first_token):
            continue
        
        # Detectar header de etapa
        if re.search(r"(MEZCLAR|MELANGER|DISPERSAR|COWLES|DISOL)", U):
            etapa = stage_from_line(ln_stripped, "")
            etapa_headers.append((idx, etapa))
    
    # Asignar etapas a ingredientes
    rows = []
    
    for ing_idx, ingrediente in ingredientes:
        # Buscar el header de etapa que viene DESPUÉS de este ingrediente
        etapa_asignada = "Preparación base"  # Default
        
        for header_idx, etapa_nombre in etapa_headers:
            if header_idx > ing_idx:
                # Este es el header que viene después
                etapa_asignada = etapa_nombre
                break
        
        # Si no hay header después, es la última sección
        if etapa_asignada == "Preparación base" and etapa_headers:
            # Verificar si está después del último header
            ultimo_header_idx = etapa_headers[-1][0]
            if ing_idx > ultimo_header_idx:
                etapa_asignada = "Mezcla final (2–3 min)"
        
        ingrediente["etapa"] = etapa_asignada
        rows.append(ingrediente)
    
    return rows

# ==================== ENSAMBLE FINAL ====================

COLUMNS = [
    "formula_key","version","tipo","color","presentación",
    "gal_producir","P/G","Volumen",
    "etapa","CODIGO","Nombre","CANT","UNIDAD",
    "Densidad (KG/GL)","KG","GL","KG/PRO","GL/PRO"
]


def parse_text_to_df(text, presentacion="STANDARD", version="1.0", brand_code=None, tipo_override=None, override_key=None):
    """
    Función principal v2.9:
    - Extrae metadata, ingredientes y devuelve DataFrame en formato estándar.
    - Soporta tipo_override desde Streamlit (prioritario sobre detección automática).
    - No fuerza normalizaciones; solo reporta.
    
    Args:
        text (str): Texto crudo de fórmula
        presentacion (str): "STANDARD" por defecto
        version (str): "1.0" por defecto
        brand_code (str): "IN" o "PM" (override manual de marca)
        tipo_override (str): Tipo manual desde dropdown (ej: "ACRILICA SUPERIOR HP")
        override_key (str): Formula_key completa manual (máxima prioridad)
    
    Returns:
        tuple: (meta, formula_key, df)
    """
    meta = extract_metadata(text)
    rows = parse_rows(text)

    # 🆕 OVERRIDE DEL TIPO (prioridad sobre detección automática)
    if tipo_override:
        meta["tipo"] = tipo_override
        print(f"✅ Tipo override aplicado: {tipo_override}")
    
    meta["presentación"] = presentacion or "STANDARD"
    meta["version"] = version or "1.0"
    
    fkey = build_formula_key(meta, brand_code=brand_code, override_key=override_key)

    out = []
    for r in rows:
        out.append({
            "formula_key": fkey,
            "version": meta["version"],
            "tipo": meta.get("tipo"),
            "color": meta.get("color"),
            "presentación": meta.get("presentación"),
            "gal_producir": meta.get("gal_producir"),
            "P/G": meta.get("P/G"),
            "Volumen": meta.get("Volumen"),
            "etapa": r.get("etapa"),
            "CODIGO": r.get("CODIGO"),
            "Nombre": r.get("Nombre"),
            "CANT": r.get("CANT"),
            "UNIDAD": r.get("UNIDAD"),
            "Densidad (KG/GL)": r.get("Densidad (KG/GL)"),
            "KG": r.get("KG"),
            "GL": r.get("GL"),
            "KG/PRO": r.get("KG/PRO"),
            "GL/PRO": r.get("GL/PRO"),
        })

    df = pd.DataFrame(out, columns=COLUMNS)
    return meta, fkey, df


# ==================== VALIDACIONES ====================

def validate_formula(df, meta, cant_tolerance=2.0, pg_tolerance=0.5, gal_tolerance=5.0):
    """
    Validaciones clave (sin maquillar resultados):
      - Σ(CANT) ~ 100 (tolerancia configurable)
      - Consistencia física: ver validate_physical_consistency()
    """
    issues = []

    # 1) Suma de CANT ~ 100 (reportar, no forzar)
    if "CANT" in df.columns and df["CANT"].notna().any():
        suma_cant = df["CANT"].fillna(0).sum()
        if not (100 - cant_tolerance <= suma_cant <= 100 + cant_tolerance):
            issues.append(f"⚠️  Suma CANT = {suma_cant:.2f} (esperado ~100)")

    # 2) Consistencia física principal (dos relaciones)
    phys_results, phys_issues = validate_physical_consistency(df, meta, pg_tolerance, gal_tolerance)
    issues.extend(phys_issues)

    return issues, phys_results


def validate_physical_consistency(df, meta, tolerance_pg=0.5, tolerance_gal=5.0):
    """
    Chequeos físicos solicitados:
      (1) Σ(KG) / Σ(GALONES) ≈ P/G
      (2) Σ(GL/PRO) ≈ gal_producir
    """
    issues = []
    results = {}

    sum_kg = df["KG"].fillna(0).sum() if "KG" in df.columns else 0.0
    sum_gl = df["GL"].fillna(0).sum() if "GL" in df.columns else 0.0
    sum_glpro = df["GL/PRO"].fillna(0).sum() if "GL/PRO" in df.columns else 0.0

    pg_meta = meta.get("P/G")
    gal_meta = meta.get("gal_producir")

    # (1) P/G
    if pg_meta and sum_gl > 0:
        pg_calc = sum_kg / sum_gl
        results["P/G_calculado"] = round(pg_calc, 3)
        if abs(pg_calc - pg_meta) > tolerance_pg:
            issues.append(f"⚠️  P/G calculado {pg_calc:.2f} vs esperado {pg_meta:.2f}")

    # (2) Galones
    if gal_meta and sum_glpro > 1.0:
        results["GL/PRO_total"] = round(sum_glpro, 2)
        if abs(sum_glpro - gal_meta) > tolerance_gal:
            issues.append(f"⚠️  gal_producir {gal_meta:.1f} vs Σ(GL/PRO) {sum_glpro:.1f}")

    return results, issues


def display_summary(meta, fkey, df):
    """Resumen compacto + validaciones clave."""
    print("="*70)
    print("✅ FÓRMULA PROCESADA - v2.4")
    print("="*70)
    print(f"Formula Key:    {fkey}")
    print(f"Tipo:           {meta.get('tipo')}")
    print(f"Color:          {meta.get('color')}")
    print(f"Gal a producir: {meta.get('gal_producir')}")
    print(f"P/G:            {meta.get('P/G')}")
    print(f"Volumen:        {meta.get('Volumen')}")
    print(f"Ingredientes:   {len(df)}")
    etapas = df["etapa"].unique().tolist() if "etapa" in df.columns and len(df) else []
    print(f"Etapas:         {', '.join(etapas) if etapas else '-'}")
    print("="*70)

    issues, phys = validate_formula(df, meta)
    if issues:
        print("\n⚠️  ADVERTENCIAS:")
        for i in issues: print(f"   {i}")
    else:
        print("\n✅ Validaciones base OK")

    # Chequeos físicos explícitos
    sum_kg = df["KG"].fillna(0).sum() if "KG" in df.columns else 0.0
    sum_gl = df["GL"].fillna(0).sum() if "GL" in df.columns else 0.0
    pg_calc = (sum_kg / sum_gl) if sum_gl > 0 else None
    sum_glpro = df["GL/PRO"].fillna(0).sum() if "GL/PRO" in df.columns else 0.0

    print("\n⚙️  Chequeos físicos clave:")
    if pg_calc is not None:
        print(f"   Σ(KG)={sum_kg:.2f} | Σ(GL)={sum_gl:.2f} | P/G calc={pg_calc:.2f} | P/G meta={meta.get('P/G')}")
    else:
        print(f"   Σ(KG)={sum_kg:.2f} | Σ(GL)={sum_gl:.2f} (sin GL no se puede calcular P/G)")
    print(f"   Σ(CANT)={df['CANT'].fillna(0).sum():.2f} | Σ(GL/PRO)={sum_glpro:.2f} | gal_producir={meta.get('gal_producir')}")


# ==================== EJEMPLO LOCAL ====================
if __name__ == "__main__":
    raw_text = """	ACRILICA SATINADA			VOLUMEN	P/G	COSTO	FECHA	GALONES PRODUCIDOS					
	BLANCO CON WHITE ULTRA			21.3335	4.72	7.11	9-jun.-22						
	STANDARD	150											
CODIGO	NOMBRE GENERICO	CANT	UNIDAD	KG/GL	KG	GALONES	PRECIO US$/KG	COSTO TOTAL RD$	OA	pvc	Xi	KG/PRO	GL/PRO
SV-0001	AGUA	25.000	KG	3.778	25.00	6.62	0.0000	$0.00				175.78	46.52
AV-004	K.T.P.P./CALGON N	0.100	KG	9.07	0.10	0.01	2.4000	$0.24				0.70	0.08
MEZCLAR DUEANTE 2 A 3 MINUTOS													
AV-011	NONYL FENOL	0.250	KG	4.01	0.25	0.06	5.0000	$1.25				1.76	0.44
AV-003	FALDEN 230	0.200	KG	3.36	0.20	0.06	4.5000	$0.90				1.41	0.42
AV-019	DISPERBLANC 7045	0.300	KG	4.50	0.30	0.07	2.5000	$0.75				2.11	0.47
SV-0005	ETHYLENE GLYCOL	1.000	KG	4.21	1.00	0.24	3.5000	$3.50				7.03	1.67
MELANGER 2 A 3 MINUTES. AJOUTER EN AUGMENTANT LA VITESSE													
PE-001	 BOOM R760/BLR 698	15.000	KG	15.48	15.00	0.97	4.7500	$71.25	18.0000	18.44	0.5556	105.47	6.81
PE-006	GALIMAN MALLA 400 SUPER BLANCO	12.000	KG	10.21	12.00	1.18	0.2000	$2.40	20.0000	22.37	0.4444	84.37	8.26
DISPERSAR DURANTE 15 MINUTOS													
COWLES 20 MNS A 1600-2800.CONTOLE PATE													
AV-020	BERMOCOLLE EBM-5500	0.280	KG	3.81	0.28	0.07	8.5000	$2.38				1.97	0.52
SV-0001	AGUA	5.000	KG	3.78	5.00	1.32	0.0000	$0.00				35.16	9.30
AV-023	FALAMINA PLUS	0.100	KG	3.40	0.10	0.03	4.0000	$0.40				0.70	0.21
DISOL VER DURANTE 5 A 10 MINUTOS													
RV-001	RESINA EP-6400/SYNTHACRIL 030 01 A50/ 	25.000	KG	3.94	25.00	6.35	2.2500	$56.25				175.78	44.63
SV-0002	TEXANOL/ NEXCOAT 795	1.500	KG	3.58	1.50	0.42	4.5000	$6.75				10.55	2.94
AV-009	IPELBP504	0.300	KG	4.52	0.30	0.07	2.5000	$0.75				2.11	0.47
AV-013	IPEL FAP 492/PREVENTOL A-14D	0.400	KG	3.99	0.40	0.10	7.5000	$3.00				2.81	0.70
MEZCLAR DURANTE 2 A 3 MINUTOS													
AV-003	FALDEN 230	0.200	KG	3.36	0.20	0.06	4.5000	$0.90				1.41	0.42
SV-0001	AGUA	14.000	KG	3.78	14.00	3.71	0.0000	$0.00				98.44	26.05
AV-024	AROMA DE BEBE	0.050	KG	3.98	0.05	0.01	19.0000	$0.95				0.35	0.09
TOTAL		100.68			100.68	21.33		 151.67 		40.81	1.00	 707.90 	 150.00 """

    meta, fkey, df = parse_text_to_df(
        raw_text,
        brand_code="IN",
        override_key=None
    )
    display_summary(meta, fkey, df)
    print(df)  # Descomenta para ver la tabla completa
