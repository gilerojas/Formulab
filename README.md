# 🧪 FORMULAB – Sistema de Fórmulas GREQ

Formulab es la plataforma interna de GREQ para operar el ciclo completo de fórmulas de pintura: captura, validación, escalamiento, emisión de órdenes de producción y notificación a planta. Está construida sobre Streamlit con un núcleo propio (`formulab/`) que centraliza el parser, las reglas de negocio y la integración con Google Sheets.

---

## ¿Qué resuelve?
- **Parser inteligente**: convierte texto plano (copiado desde Excel/PDF) en DataFrames listos para escalar (`scripts/formulas_core.py`, `formulab/formulab_api.py`).
- **Motor de escalamiento**: calcula ingredientes y unidades para diferentes galonajes manteniendo la relación peso/galón.
- **Validaciones de calidad**: reglas de consistencia por marca/tipo con feedback visual en la UI (`components/validators.py`).
- **Gestión de catálogo**: lectura/escritura centralizada en Google Sheets (módulos en `formulab/sheets/`).
- **Órdenes listas para planta**: genera PDFs estilizados (`utils/pdf_generator.py`) y dispara notificaciones opcionales por WhatsApp (`utils/whatsapp_notifier.py`).

---

## Arquitectura a alto nivel
- **app.py**: bootstrap de Streamlit, navegación y estilos globales.
- **pages/**: páginas multipaso (`home`, `nueva_formula`, `catalogo`, `generar_orden`).
- **formulab/**: paquete instalable con conectores, motor y API pública para la UI.
- **components/**: tarjetas, tablas y validadores reutilizables en Streamlit.
- **utils/**: helpers de estilo, PDF y notificaciones.
- **scripts/**: utilidades CLI / batch (parser core, inicialización de Sheets, etc.).
- **tests/** y **tests_orden_pdf/**: pruebas unitarias e2e del parser y del layout de órdenes.

```
.
├── app.py
├── pages/
│   ├── home.py
│   ├── nueva_formula.py
│   ├── catalogo.py
│   └── generar_orden.py
├── formulab/
│   ├── formulab_api.py
│   ├── sheets/
│   │   ├── sheets_connector.py
│   │   ├── formulas_manager.py
│   │   ├── ordenes_manager.py
│   │   └── tipo_mapeo_manager.py
│   └── ...
├── components/
├── utils/
├── scripts/
├── tests/
└── requirements.txt
```

---

## Flujos principales
1. **Validar una nueva fórmula**
   - Ingresar metadata (marca, tipo) en `pages/nueva_formula.py`.
   - Pegar el texto crudo; el parser detecta encabezados, etapas, densidades y calcula métricas clave.
   - Revisar issues y, si es válida, guardar directo en Google Sheets con `formulas_manager`.

2. **Generar una orden de producción**
   - Seleccionar fórmula existente, galones objetivo y referencias (PED/BATCH).
   - El motor escala cantidades, genera tablas comparativas y crea un PDF firmado (`utils/pdf_generator.py`).
   - Opcional: notificar por WhatsApp al grupo técnico usando WaSenderAPI.

3. **Administrar catálogo**
   - La página `catalogo.py` consulta las hojas `GREQ_Formulas` y `Formulas_Detalle` para explorar/buscar fórmulas.

4. **Automatizaciones**
   - `scripts/` contiene helpers para inicializar hojas (`sheets_connector.initialize_sheets`) o ejecutar el parser desde CLI para lotes históricos.

---

## Requisitos
- Python 3.9+ (recomendado 3.11).
- Credencial de servicio de Google (JSON) con acceso a Sheets/Drive.
- Cuenta WaSenderAPI (opcional) para notificaciones.
- Dependencias listadas en `requirements.txt` (Streamlit, pandas, gspread, reportlab, etc.).

---

## Configuración rápida
1. **Crear entorno e instalar dependencias**
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install --upgrade pip
   pip install -r requirements.txt
   ```
2. **Credenciales de Google**
   - Colocar el JSON de la service account en la raíz del repo (por defecto `vocal-tracker-453720-p1-2c9dfa471a22.json`).
   - Alternativamente cargar `st.secrets["gcp_service_account"]` cuando se despliega en Streamlit Cloud.
3. **Variables `.env` (opcional)**
   ```
   WASENDER_API_KEY=tu_token_wasender
   GROUP_GREQ_TECNICO=numero_o_grupo
   ```
4. **Lanzar la app**
   ```bash
   streamlit run app.py
   ```

---

## Variables y secretos

| Variable / archivo                         | Dónde vive                         | Uso |
|-------------------------------------------|------------------------------------|-----|
| `vocal-tracker-...json`                   | raíz del repo / `st.secrets`       | Autenticación Google Sheets/Drive |
| `SPREADSHEET_ID` (en `sheets_connector`)   | `formulab/sheets/sheets_connector.py` | Selecciona el spreadsheet maestro |
| `WASENDER_API_KEY`, `GROUP_GREQ_TECNICO`   | `.env` o variables del sistema     | Token y destino de WhatsApp |
| `.streamlit/config.toml`                  | `.streamlit/`                      | Temas y secrets locales de Streamlit |

---

## Scripts y módulos destacados
- `scripts/formulas_core.py`: núcleo del parser, reglas de escalamiento y normalización de DataFrames.
- `formulab/sheets/*.py`: conectores CRUD hacia cada hoja (fórmulas, detalle, órdenes, tipos).
- `utils/pdf_generator.py`: plantilla oficial de órdenes (ReportLab).
- `utils/styling.py`: estilos globales para la UI.
- `utils/whatsapp_notifier.py`: helper para WaSenderAPI.

---

## Pruebas
Ejecuta `pytest` para validar el parser y los cálculos de órdenes:
```bash
pytest -q
```
El directorio `tests_orden_pdf/` incluye comparaciones visuales del layout PDF; se recomienda ejecutarlas tras cambios en `utils/pdf_generator.py`.

---

## Despliegue
- 🛰️ **Streamlit Cloud**: instancia oficial publicada el 17 de diciembre de 2025. Actualiza `st.secrets` con las credenciales y el `.env` remoto antes de hacer deploy.
- 🖥️ **Local**: `streamlit run app.py` siguiendo la sección de configuración rápida.

---

## Soporte
- 💬 Equipo interno: `st.sidebar` muestra correos y versiones.
- 📧 Contacto principal: [gilerojas@gmail.com](mailto:gilerojas@gmail.com)
- 🛠️ Scripts auxiliares: `init_formulab.sh` instala dependencias mínimas en entornos limpios.
