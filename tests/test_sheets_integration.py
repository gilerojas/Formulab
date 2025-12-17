"""
Test de integración Formulab + Google Sheets
"""

from formulab.formulab_api import procesar_formula
from formulab.sheets import (
    initialize_sheets,
    guardar_formula,
    buscar_formula,
    listar_formulas,
    generar_orden,
    obtener_ordenes_pendientes
)

# Fórmula de ejemplo
raw_formula = """
ACRILICA SUPERIOR HP    VOLUMEN    P/G
BLANCO 100-66           100        5.46

CODIGO    NOMBRE                CANT    UNIDAD    KG/GL
SV-0001   AGUA                  12.00   KG        3.78
RV-0002   RESINA ACRILICA       25.00   KG        4.20
PG-0003   PIGMENTO BLANCO       45.00   KG        5.80
AD-0004   ADITIVO DISPERSANTE    8.00   KG        4.50
AD-0005   ESPESANTE             10.00   KG        4.10
TOTAL                          100.00            21.33
"""

def test_completo():
    print("\n" + "="*60)
    print("🧪 TEST INTEGRACIÓN FORMULAB + GOOGLE SHEETS")
    print("="*60)
    
    # 1. Inicializar hojas
    print("\n📋 PASO 1: Inicializar hojas...")
    initialize_sheets()
    
    # 2. Procesar y guardar fórmula
    print("\n📋 PASO 2: Procesar y guardar fórmula...")
    result = procesar_formula(raw_formula, gal_objetivo=100)
    fkey, success = guardar_formula(
        result,
        observaciones="Fórmula estándar de producción"
    )
    
    # 3. Buscar fórmula
    print("\n📋 PASO 3: Buscar fórmula guardada...")
    formula = buscar_formula(fkey)
    if formula:
        print(f"✅ Fórmula encontrada:")
        print(f"  - Key: {formula['Formula_Key']}")
        print(f"  - Tipo: {formula['Tipo']}")
        print(f"  - Color: {formula['Color']}")
        print(f"  - Volumen Base: {formula['Volumen_Base']} gal")
        print(f"  - P/G: {formula['PG_Pintura']}")
    
    # 4. Listar fórmulas
    print("\n📋 PASO 4: Listar fórmulas...")
    df_formulas = listar_formulas()
    print(f"Total fórmulas: {len(df_formulas)}")
    
    # 5. Generar orden de producción
    print("\n📋 PASO 5: Generar orden de producción (25 gal)...")
    orden_id, df_escalado, success = generar_orden(
        formula_key=fkey,
        gal_objetivo=25,
        usuario="Gilberto Rojas",
        ped_id="PED-2025-150"
    )
    
    if success:
        print(f"✅ Orden generada: {orden_id}")
        print(f"\n📊 Ingredientes escalados (top 3):")
        print(df_escalado[["nombre", "CANT", "KG_PRO", "GL_PRO"]].head(3))
    
    # 6. Ver órdenes pendientes
    print("\n📋 PASO 6: Ver órdenes pendientes...")
    df_pendientes = obtener_ordenes_pendientes()
    print(f"Órdenes pendientes: {len(df_pendientes)}")
    
    print("\n" + "="*60)
    print("✅ TEST COMPLETADO")
    print("="*60 + "\n")
    
def debug_datos_formula():
    """
    Compara los datos originales vs los datos guardados/leídos.
    """
    from formulab.formulab_api import procesar_formula
    from formulab.sheets import obtener_ingredientes_formula
    
    print("\n" + "="*60)
    print("🔍 DEBUG: Comparación de datos")
    print("="*60)
    
    # Procesar fórmula original
    result = procesar_formula(raw_formula, gal_objetivo=100)
    df_original = result["df_escalado"]
    
    print("\n📊 Datos ORIGINALES (procesados):")
    print(f"  - Total ingredientes: {len(df_original)}")
    print(f"  - Suma CANT: {df_original['CANT'].sum():.2f}")
    print(f"  - Suma KG_PRO: {df_original['KG_PRO'].sum():.2f}")
    print(f"  - Suma GL_PRO: {df_original['GL_PRO'].sum():.2f}")
    print(f"  - P/G calculado: {result['metrics']['pg_calculado']:.2f}")
    print("\nTop 3 ingredientes:")
    print(df_original[["nombre", "CANT", "KG_PRO", "GL_PRO"]].head(3))
    
    # Leer desde Sheets
    df_leido = obtener_ingredientes_formula("PM-SUP-BLANCO100-66")
    
    print("\n📊 Datos LEÍDOS (desde Sheets):")
    print(f"  - Total ingredientes: {len(df_leido)}")
    print(f"  - Suma Cantidad: {df_leido['Cantidad'].sum():.2f}")
    print("\nTop 3 ingredientes:")
    print(df_leido[["Nombre", "Cantidad", "Densidad_KG_GL"]].head(3))
    
    print("\n" + "="*60)

def debug_pg_profundo():
    """
    Debug detallado del cálculo de P/G
    """
    from formulab.formulab_api import procesar_formula
    
    print("\n" + "="*60)
    print("🔍 DEBUG PROFUNDO: Cálculo P/G")
    print("="*60)
    
    # Procesar fórmula original
    result = procesar_formula(raw_formula, gal_objetivo=100)
    df = result["df_escalado"]
    
    print("\n📊 Valores individuales:")
    print(df[["nombre", "CANT", "Densidad_KG_GL", "KG", "GL"]].to_string())
    
    print("\n🧮 Cálculos paso a paso:")
    print(f"  - Σ(CANT): {df['CANT'].sum():.2f}")
    print(f"  - Σ(KG): {df['KG'].sum():.2f}")
    print(f"  - Σ(GL): {df['GL'].sum():.2f}")
    print(f"  - P/G manual = KG/GL: {df['KG'].sum() / df['GL'].sum():.4f}")
    
    print("\n📊 Metrics del resultado:")
    print(f"  - P/G reportado: {result['metrics']['pg_calculado']:.4f}")
    print(f"  - P/G esperado: {result['meta']['P/G']:.4f}")
    
    print("\n🔢 Fila por fila (GL calculado):")
    for idx, row in df.iterrows():
        gl_calc = row['KG'] / row['Densidad_KG_GL']
        print(f"  {row['nombre'][:20]:20s} | KG={row['KG']:6.2f} | Dens={row['Densidad_KG_GL']:5.2f} | GL={row['GL']:6.2f} | GL_calc={gl_calc:6.2f}")
    
    print("="*60)

if __name__ == "__main__":
    debug_pg_profundo()