"""
WhatsApp Notifier para Órdenes de Producción
Integración con WaSenderAPI usando variables de entorno
"""

import requests
import os
from datetime import datetime
from dotenv import load_dotenv


def _get_whatsapp_config():
    """Carga credenciales solo al enviar, no al importar la página."""
    token = os.getenv("WASENDER_API_KEY")
    group = os.getenv("GROUP_GREQ_TECNICO")

    if token and group:
        return token, group

    load_dotenv()
    return os.getenv("WASENDER_API_KEY"), os.getenv("GROUP_GREQ_TECNICO")


def enviar_notificacion_orden(
    orden_id: str,
    formula_info: dict,
    galones: float,
    ped_id: str = "",
    batch_id: str = "",
):
    """
    Envía notificación WhatsApp al generar orden.
    
    Args:
        orden_id: ID de la orden (ej: ORD-2025-001)
        formula_info: Dict con metadata de fórmula
        galones: Galones a producir
        ped_id: PED_ID opcional
        batch_id: Batch ID opcional
    
    Returns:
        bool: True si envío exitoso
    """
    
    was_token, group_greq_formulab = _get_whatsapp_config()

    # Validar credenciales
    if not was_token or not group_greq_formulab:
        print("❌ Error: WASENDER_API_KEY o GROUP_ID_TEST no configurados en .env")
        return False
    
    # Construir mensaje
    fecha_actual = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    tipo = formula_info.get("Tipo", "N/A")
    color = formula_info.get("Color", "N/A")
    pg = float(formula_info.get("PG_Pintura", 0))
    marca = formula_info.get("Marca", "N/A")
    
    mensaje = f"""🏭 *NUEVA ORDEN DE PRODUCCIÓN*

📋 Orden: *{orden_id}*
🎨 Fórmula: {marca} {tipo} - {color}
📊 Volumen: *{galones} galones*"""
    
    # Agregar referencias si existen
    if ped_id or batch_id:
        mensaje += "\n\n🔗 Referencias:"
        if ped_id:
            mensaje += f"\n  • PED_ID: {ped_id}"
        if batch_id:
            mensaje += f"\n  • Batch ID: {batch_id}"
    
    mensaje += f"\n\n📄 PDF generado y listo para producción\n⏰ {fecha_actual}\n\n_Sistema Formulab | GREQ_"
    
    # Enviar vía WaSenderAPI
    try:
        url = "https://www.wasenderapi.com/api/send-message"
        
        headers = {
            "Authorization": f"Bearer {was_token}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "to": group_greq_formulab,
            "text": mensaje
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        
        if response.status_code == 200:
            print(f"✅ Notificación WhatsApp enviada: {orden_id}")
            return True
        else:
            print(f"❌ Error WhatsApp ({response.status_code}): {response.text}")
            return False
    
    except Exception as e:
        print(f"❌ Error enviando WhatsApp: {e}")
        return False
