"""
Funciones de formateo para números, volúmenes, porcentajes
"""


def format_number(value: float, decimals: int = 2, sep: str = ",") -> str:
    """
    Formatea número con separador de miles.
    
    Args:
        value: Número a formatear
        decimals: Decimales a mostrar
        sep: Separador de miles (. o ,)
    
    Returns:
        String formateado
    """
    if value is None:
        return "—"
    
    formatted = f"{value:.{decimals}f}"
    parts = formatted.split(".")
    
    # Agregar separador de miles
    integer_part = parts[0]
    if len(integer_part) > 3:
        integer_part = f"{int(integer_part):,}".replace(",", sep if sep == "," else ".")
    
    return f"{integer_part}.{parts[1]}" if len(parts) > 1 else integer_part


def format_percentage(value: float, decimals: int = 1) -> str:
    """Formatea como porcentaje"""
    if value is None:
        return "—"
    return f"{value*100:.{decimals}f}%"


def format_volume(value: float, unit: str = "gal") -> str:
    """
    Formatea volumen con unidad.
    
    Args:
        value: Volumen
        unit: Unidad (gal, L, mL, etc)
    
    Returns:
        String formateado
    """
    return f"{format_number(value, 2)} {unit}"


def format_kg_per_gal(value: float) -> str:
    """Formatea P/G (kg/galón)"""
    if value is None:
        return "—"
    return f"{value:.2f} kg/gal"