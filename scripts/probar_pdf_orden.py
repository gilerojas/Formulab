#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Prueba del generador de PDF de ordenes (layout inteligente).
Genera dos PDFs: pocos items (fuente grande) y muchos items (una hoja).
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from utils.pdf_generator import generar_pdf_orden

FORMULA_INFO = {
    "Formula_Key": "F-TEST-001",
    "Marca": "GREQ",
    "Tipo": "Acrilica",
    "Color": "Blanco",
}

def main():
    out_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "tmp_pdf_test")
    os.makedirs(out_dir, exist_ok=True)

    # 1) Pocos items -> fuente grande
    df_poco = pd.DataFrame([
        {"etapa": "Base", "CODIGO": "SV-0001", "nombre": "Agua", "KG_PRO": 12.5, "GL_PRO": 3.2},
        {"etapa": "Base", "CODIGO": "RV-0002", "nombre": "Resina acrilica", "KG_PRO": 25.0, "GL_PRO": 6.0},
        {"etapa": "Pigmento", "CODIGO": "PV-0001", "nombre": "Dioxido de titanio", "KG_PRO": 8.0, "GL_PRO": 2.0},
    ])
    path_poco = os.path.join(out_dir, "orden_pocos_items.pdf")
    generar_pdf_orden(
        "ORD-PRUEBA-POCOS",
        FORMULA_INFO,
        df_poco,
        25.0,
        output_path=path_poco,
    )
    print("OK Generado (pocos items):", path_poco)

    # 2) Muchos items -> todo en una hoja
    filas = []
    for i in range(45):
        etapa = "Base" if i < 25 else "Pigmento"
        filas.append({
            "etapa": etapa,
            "CODIGO": f"X{i+1:03d}",
            "nombre": f"Ingrediente de prueba numero {i+1}",
            "KG_PRO": round(1.0 + i * 0.15, 2),
            "GL_PRO": round(0.2 + i * 0.05, 2),
        })
    df_muchos = pd.DataFrame(filas)
    path_muchos = os.path.join(out_dir, "orden_muchos_items.pdf")
    generar_pdf_orden(
        "ORD-PRUEBA-MUCHOS",
        FORMULA_INFO,
        df_muchos,
        100.0,
        output_path=path_muchos,
    )
    print("OK Generado (muchos items):", path_muchos)

    print("\nAbre los PDFs en", out_dir, "para revisar.")
    if sys.platform == "darwin":
        os.system(f'open "{path_poco}"')
        os.system(f'open "{path_muchos}"')


if __name__ == "__main__":
    main()
