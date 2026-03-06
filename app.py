"""
Sistema de Recordatorios de Gotas Oftalmológicas vía WhatsApp
===============================================================
Este sistema recibe un mensaje de WhatsApp para iniciar el día,
calcula los horarios de las 5 gotas según sus intervalos, y envía
recordatorios automáticos a cada hora programada.

Gotas configuradas:
- LOTEREX 0.5%: cada 8 horas
- SUERO AUTOLOGO: cada 4 horas
- SYSTANE HIDRATACION SP: cada 2 horas
- THEALOZ: cada 1 hora
- CICLOSPORINA A: cada 8 horas
"""

import os
from datetime import datetime, timedelta
from flask import Flask, request, jsonify
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse
import pytz
import logging
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Configuración
app = Flask(__name__)

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Credenciales de Twilio
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
TWILIO_WHATSAPP_NUMBER = os.getenv('TWILIO_WHATSAPP_NUMBER')
USER_WHATSAPP_NUMBER = os.getenv('USER_WHATSAPP_NUMBER', '+5219612254590')

# Números para enviar recordatorios (ambos reciben los mensajes)
GIRLFRIEND_NUMBER = '+5219612324432'  # Número de tu novia
YOUR_NUMBER = '+5219612254590'  # Tu número

# Zona horaria de México
TIMEZONE = 'America/Mexico_City'
tz = pytz.timezone(TIMEZONE)

# Configuración de las gotas
DROPS_CONFIG = {
    'LOTEREX 0.5%': {'interval_hours': 8, 'emoji': '💊'},
    'SUERO AUTOLOGO': {'interval_hours': 4, 'emoji': '🧴'},
    'SYSTANE HIDRATACION SP': {'interval_hours': 2, 'emoji': '💧'},
    'THEALOZ': {'interval_hours': 1, 'emoji': '👁️'},
    'CICLOSPORINA A': {'interval_hours': 8, 'emoji': '⚠️'}
}

# Configuración de notificaciones
NOTIFICATION_END_HOUR = 2  # Hasta las 2:00 AM (del día siguiente)
DROP_DELAY_MINUTES = 5  # Minutos de diferencia entre gotas que coinciden

# Inicializar cliente de Twilio
twilio_client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def send_whatsapp_message(to_number, message_body):
    """Envía un mensaje de WhatsApp usando Twilio."""
    try:
        # Asegurar que el número tenga el formato correcto con prefijo +
        if not to_number.startswith('+'):
            to_number = '+' + to_number

        from_number = TWILIO_WHATSAPP_NUMBER
        if not from_number.startswith('+'):
            from_number = '+' + from_number

        logger.info(f"Enviando mensaje de {from_number} a {to_number}")

        message = twilio_client.messages.create(
            body=message_body,
            from_=f'whatsapp:{from_number}',
            to=f'whatsapp:{to_number}'
        )
        logger.info(f"Mensaje enviado a {to_number}: {message_body[:50]}...")
        return True
    except Exception as e:
        logger.error(f"Error al enviar mensaje a {to_number}: {e}")
        return False


def send_to_both_numbers(message_body):
    """Envía un mensaje a ambos números (novia y tú)."""
    logger.info(f"Enviando mensaje a ambos números...")
    result1 = send_whatsapp_message(GIRLFRIEND_NUMBER, message_body)
    logger.info(f"Resultado enviar a novia: {result1}")
    result2 = send_whatsapp_message(YOUR_NUMBER, message_body)
    logger.info(f"Resultado enviar a ti: {result2}")


def schedule_whatsapp_message_twilio(to_number, message_body, send_time):
    """Programa un mensaje usando Twilio (más confiable que APScheduler)."""
    try:
        if not to_number.startswith('+'):
            to_number = '+' + to_number

        from_number = TWILIO_WHATSAPP_NUMBER
        if not from_number.startswith('+'):
            from_number = '+' + from_number

        # Convertir tiempo a formato ISO
        scheduled_time = send_time.strftime('%Y-%m-%dT%H:%M:%SZ')

        message = twilio_client.messages.create(
            body=message_body,
            from_=f'whatsapp:{from_number}',
            to=f'whatsapp:{to_number}',
            schedule_type='fixed',
            send_at=scheduled_time
        )
        logger.info(f"Mensaje programado para {to_number} a las {scheduled_time}: {message_body[:30]}...")
        return True
    except Exception as e:
        logger.error(f"Error al programar mensaje para {to_number}: {e}")
        return False


def schedule_to_both_twilio(message_body, send_time):
    """Programa un mensaje a ambos números usando Twilio."""
    logger.info(f"Programando mensaje para ambos a las {send_time}...")
    result1 = schedule_whatsapp_message_twilio(GIRLFRIEND_NUMBER, message_body, send_time)
    result2 = schedule_whatsapp_message_twilio(YOUR_NUMBER, message_body, send_time)
    return result1 and result2


def calculate_drop_schedule(start_time):
    """
    Calcula los horarios de todas las gotas basándose en la hora de inicio.
    Genera horarios hasta las 1:00 AM del día siguiente.
    """
    schedule = {}

    # Calcular hora final (1 AM del día siguiente)
    if NOTIFICATION_END_HOUR < start_time.hour:
        # Si la hora final es menor que la hora actual, es del día siguiente
        tomorrow = start_time.date() + timedelta(days=1)
        end_of_day = datetime.combine(tomorrow, datetime.min.time().replace(hour=NOTIFICATION_END_HOUR))
        end_of_day = tz.localize(end_of_day)
    else:
        end_of_day = start_time.replace(hour=NOTIFICATION_END_HOUR, minute=0, second=0, microsecond=0)

    for drop_name, config in DROPS_CONFIG.items():
        interval = config['interval_hours']
        emoji = config['emoji']

        drop_times = []
        current_time = start_time

        # Generar horarios hasta las 1:00 AM
        while current_time <= end_of_day:
            drop_times.append({
                'time': current_time,
                'name': drop_name,
                'emoji': emoji
            })
            current_time += timedelta(hours=interval)

        schedule[drop_name] = drop_times

    return schedule


def group_drops_by_time(schedule):
    """
    Agrupa las gotas por hora. Si varias gotas coinciden,
    las separa por 5 minutos de diferencia.
    """
    time_slots = {}

    for drop_name, drop_times in schedule.items():
        for drop_info in drop_times:
            time_key = drop_info['time'].strftime('%Y-%m-%d %H:%M')

            if time_key not in time_slots:
                time_slots[time_key] = {
                    'datetime': drop_info['time'],
                    'drops': []
                }

            time_slots[time_key]['drops'].append({
                'name': drop_info['name'],
                'emoji': drop_info['emoji']
            })

    # Si hay más de una gota en el mismo horario, separarlas por 5 minutos
    final_schedule = []
    for time_key, slot_data in sorted(time_slots.items(), key=lambda x: x[1]['datetime']):
        if len(slot_data['drops']) > 1:
            # Separar gotas por 5 minutos
            for i, drop in enumerate(slot_data['drops']):
                adjusted_time = slot_data['datetime'] + timedelta(minutes=i * DROP_DELAY_MINUTES)
                final_schedule.append({
                    'datetime': adjusted_time,
                    'drops': [drop]
                })
        else:
            final_schedule.append(slot_data)

    # Ordenar por tiempo final
    final_schedule.sort(key=lambda x: x['datetime'])

    return [(f"drop_{i}", slot) for i, slot in enumerate(final_schedule)]


def schedule_drop_reminders(start_time, user_number=None):
    """
    Programa todos los recordatorios de gotas para el día.
    """
    # Usar el número proporcionado o el por defecto
    target_number = user_number if user_number else USER_WHATSAPP_NUMBER

    # Calcular horarios
    schedule = calculate_drop_schedule(start_time)
    grouped_schedule = group_drops_by_time(schedule)
    logger.info(f"Total de horarios programados: {len(grouped_schedule)}")

    # Mensaje de confirmación con agenda completa
    now_local = datetime.now(tz)
    confirmation_msg = (
        f"✅ *PROTOCOLO INICIADO*\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"📅 {now_local.strftime('%d/%m/%Y')}\n"
        f"🕐 Inicio: {start_time.strftime('%H:%M')}\n"
        f"⏰ Hasta: 01:00 AM\n\n"
        f"📋 *AGENDA DE HOY:*\n"
    )

    for time_key, slot_data in grouped_schedule:
        time_str = slot_data['datetime'].strftime('%H:%M')
        drops_list = [f"{d['emoji']} {d['name']}" for d in slot_data['drops']]
        confirmation_msg += f"• {time_str}: {', '.join(drops_list)}\n"

    confirmation_msg += (
        f"\n━━━━━━━━━━━━━━━━━━━━━━\n"
        f"✅ Recordatorios anteriores borrados\n"
        f"💬 Escribe 'DORMIR' para detener"
    )

    # Enviar mensaje de confirmación
    logger.info("Intentando enviar mensaje de confirmación con agenda...")
    send_to_both_numbers(confirmation_msg)
    logger.info("Mensaje de confirmación enviado")

    # Programar cada recordatorio usando Twilio (más confiable)
    scheduled_count = 0
    for time_key, slot_data in grouped_schedule:
        # No programar si ya pasó la hora
        if slot_data['datetime'] <= datetime.now(tz):
            continue

        drops_list = [f"{d['emoji']} {d['name']}" for d in slot_data['drops']]
        time_str = slot_data['datetime'].strftime('%H:%M')

        reminder_message = f"{', '.join(drops_list)}"

        # Programar usando Twilio en lugar de APScheduler
        result = schedule_to_both_twilio(reminder_message, slot_data['datetime'])
        if result:
            scheduled_count += 1
            logger.info(f"Recordatorio programado para {time_str}")

    return scheduled_count


def handle_incoming_message(from_number, message_body):
    """
    Maneja los mensajes entrantes de WhatsApp.
    """
    message = message_body.strip().upper()

    # Mensajes de inicio
    if message in ['INICIAR', 'INICIO', 'HOLA', 'Buenos días', 'BUENOS DÍAS', 'START', '1']:
        now = datetime.now(tz)
        num_reminders = schedule_drop_reminders(now, from_number)

        # No enviar respuesta adicional aquí - el mensaje con la agenda ya se envió en schedule_drop_reminders
        response = (
            f"✅ ¡Perfecto! Agenda activada.\n"
            f"📅 {now.strftime('%d/%m/%Y')}\n"
            f"🕐 Inicio: {now.strftime('%H:%M')}\n"
            f"⏰ {num_reminders} recordatorios hasta 01:00 AM\n\n"
            f"Revisa el mensaje anterior con tu agenda completa 💧"
        )

    # Mensaje para dormir/detener
    elif message in ['DORMIR', 'PARAR', 'STOP', 'DETENER', '0']:
        response = (
            "🌙 Recordatorios detenidos.\n\n"
            "Para reiniciar mañana, envía 'INICIAR' cuando te despiertes."
        )

    # Mensaje de estado
    elif message in ['ESTADO', 'HORARIOS', 'AGENDA']:
        response = (
            "📋 Revisa el mensaje de confirmación con tu agenda completa."
        )

    # Ayuda
    elif message in ['AYUDA', 'HELP', '?']:
        response = (
            "📖 *COMANDOS DISPONIBLES*\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n"
            "• INICIAR - Generar horarios de gotas\n"
            "• DORMIR - Detener recordatorios\n"
            "• ESTADO - Ver horarios de hoy\n"
            "• AYUDA - Mostrar este mensaje"
        )

    # Mensaje no reconocido
    else:
        response = (
            "🤔 No entendí tu mensaje.\n\n"
            "Escribe:\n"
            "• INICIAR para comenzar\n"
            "• AYUDA para ver comandos"
        )

    return response


@app.route('/')
def index():
    """Página principal del sistema."""
    return '''
    <!DOCTYPE html>
    <html lang="es">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>💧 Sistema de Gotas</title>
        <style>
            * { margin: 0; padding: 0; box-sizing: border-box; }
            body {
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                min-height: 100vh;
                display: flex;
                justify-content: center;
                align-items: center;
                padding: 20px;
            }
            .container {
                background: white;
                border-radius: 20px;
                box-shadow: 0 20px 60px rgba(0,0,0,0.3);
                padding: 40px;
                max-width: 500px;
                width: 100%;
            }
            h1 { color: #333; text-align: center; margin-bottom: 10px; font-size: 28px; }
            .subtitle { text-align: center; color: #666; margin-bottom: 30px; }
            .drop-card {
                background: #f8f9fa;
                border-radius: 12px;
                padding: 15px;
                margin-bottom: 12px;
                border-left: 4px solid #667eea;
            }
            .drop-card:nth-child(2) { border-left-color: #4CAF50; }
            .drop-card:nth-child(3) { border-left-color: #2196F3; }
            .drop-card:nth-child(4) { border-left-color: #9C27B0; }
            .drop-card:nth-child(5) { border-left-color: #FF9800; }
            .drop-name { font-weight: bold; color: #333; font-size: 14px; }
            .drop-interval { color: #666; font-size: 12px; margin-top: 4px; }
            .instructions {
                background: #e8f4fd;
                border-radius: 12px;
                padding: 20px;
                margin-top: 20px;
            }
            .instructions h3 { color: #1976D2; margin-bottom: 10px; font-size: 16px; }
            .instructions ol { padding-left: 20px; color: #555; line-height: 1.8; }
            .whatsapp-btn {
                display: block;
                width: 100%;
                background: #25D366;
                color: white;
                text-align: center;
                padding: 15px;
                border-radius: 12px;
                text-decoration: none;
                font-weight: bold;
                margin-top: 20px;
            }
            .status {
                text-align: center;
                margin-top: 20px;
                padding: 10px;
                border-radius: 8px;
                background: #e8f5e9;
                color: #2e7d32;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>💧 Sistema de Gotas</h1>
            <p class="subtitle">Recordatorios automáticos vía WhatsApp</p>

            <div class="drop-card">
                <div class="drop-name">💊 LOTEREX 0.5%</div>
                <div class="drop-interval">Cada 8 horas</div>
            </div>

            <div class="drop-card">
                <div class="drop-name">🧴 SUERO AUTOLOGO</div>
                <div class="drop-interval">Cada 4 horas</div>
            </div>

            <div class="drop-card">
                <div class="drop-name">💧 SYSTANE HIDRATACION SP</div>
                <div class="drop-interval">Cada 2 horas</div>
            </div>

            <div class="drop-card">
                <div class="drop-name">👁️ THEALOZ</div>
                <div class="drop-interval">Cada 1 hora</div>
            </div>

            <div class="drop-card">
                <div class="drop-name">⚠️ CICLOSPORINA A</div>
                <div class="drop-interval">Cada 8 horas</div>
            </div>

            <div class="instructions">
                <h3>📱 Cómo funciona:</h3>
                <ol>
                    <li>Envía "INICIAR" por WhatsApp</li>
                    <li>Recibes la agenda del día</li>
                    <li>Te llega un recordatorio por cada gota</li>
                </ol>
            </div>

            <a href="https://wa.me/5219612254590?text=INICIAR" class="whatsapp-btn">
                💬 Enviar "INICIAR" por WhatsApp
            </a>

            <div class="status">
                ✅ Sistema activo
            </div>
        </div>
    </body>
    </html>
    '''


@app.route('/webhook', methods=['POST'])
def webhook():
    """Endpoint de webhook para recibir mensajes de Twilio."""
    try:
        from_number = request.form.get('From', '')
        message_body = request.form.get('Body', '')

        logger.info(f"Mensaje recibido de {from_number}: {message_body}")

        # Extraer número de teléfono
        if from_number and 'whatsapp:' in from_number:
            user_phone = from_number.replace('whatsapp:', '')
        else:
            user_phone = from_number

        logger.info(f"Número extraído: {user_phone}")

        response_text = handle_incoming_message(user_phone, message_body)

        twiml_response = MessagingResponse()
        twiml_response.message(response_text)

        return str(twiml_response)

    except Exception as e:
        logger.error(f"Error en webhook: {e}")
        return str(e), 500


@app.route('/health', methods=['GET'])
def health():
    """Endpoint de verificación de salud."""
    return jsonify({
        'status': 'ok',
        'timestamp': datetime.now(tz).isoformat()
    })


@app.route('/manual-trigger', methods=['POST'])
def manual_trigger():
    """Endpoint para activar manualmente los recordatorios."""
    now = datetime.now(tz)
    num_reminders = schedule_drop_reminders(now)

    return jsonify({
        'success': True,
        'message': f'Se programaron {num_reminders} recordatorios',
        'start_time': now.strftime('%H:%M')
    })


if __name__ == '__main__':
    port = int(os.getenv('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
