# 💧 Sistema de Recordatorios de Gotas Oftalmológicas

## 📋 Descripción

Sistema automatizado que envía recordatorios de gotas oculares vía WhatsApp. El sistema calcula los horarios dinámicamente según el momento en que la usuaria envíe el mensaje de activación.

## 💊 Gotas Configuradas

| Gota | Intervalo |
|------|-----------|
| LOTEREX 0.5% | Cada 8 horas |
| SUERO AUTOLOGO | Cada 4 horas |
| SYSTANE HIDRATACION SP | Cada 2 horas |
| CICLOSPORINA A | Cada 8 horas |

## 🚀 Cómo Funciona

1. **Activar**: La usuaria envía "INICIAR" por WhatsApp
2. **Calcular**: El sistema genera los horarios del día basados en la hora actual
3. **Recordar**: Envía un WhatsApp a cada hora programada
4. **Detener**: Envía "DORMIR" para detener los recordatorios

## 📱 Comandos Disponibles

- **INICIAR** - Genera la agenda de gotas del día
- **DORMIR** - Detiene todos los recordatorios
- **ESTADO** - Muestra los horarios pendientes
- **AYUDA** - Muestra los comandos disponibles

## 🛠️ Instalación Local

```bash
# Clonar el repositorio
cd eye_drops_scheduler

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # En Windows: venv\Scripts\activate

# Instalar dependencias
pip install -r requirements.txt

# Ejecutar
python app.py
```

## 🌐 Despliegue

### Opción 1: Render (Recomendado - Gratis)

1. Crear cuenta en [render.com](https://render.com)
2. Conectar repositorio GitHub
3. Crear nuevo Web Service
4. Configurar:
   - Build Command: (vacío)
   - Start Command: `python app.py`
5. Añadir variables de entorno en el panel de Render
6. Copiar la URL del servicio
7. En Twilio Dashboard → Messaging → Webhooks → Configure:
   - Messaging URL: `https://TU-SERVICIO.onrender.com/webhook`

### Opción 2: Heroku

1. Crear cuenta en [heroku.com](https://heroku.com)
2. Instalar Heroku CLI
3. Ejecutar:
   ```bash
   heroku create nombre-de-tu-app
   heroku config:set TWILIO_ACCOUNT_SID=tu_sid
   heroku config:set TWILIO_AUTH_TOKEN=tu_token
   heroku config:set TWILIO_WHATSAPP_NUMBER=tu_numero
   heroku config:set USER_WHATSAPP_NUMBER=numero_usuario
   git push heroku main
   ```

### Opción 3: PythonAnywhere

1. Crear cuenta en [pythonanywhere.com](https://pythonanywhere.com)
2. Subir archivos via Files tab
3. Configurar Web tab → WSGI configuration
4. Configurar el webhook de Twilio

## 📂 Estructura del Proyecto

```
eye_drops_scheduler/
├── app.py              # Aplicación principal Flask
├── requirements.txt   # Dependencias Python
├── .env              # Variables de entorno
├── Procfile          # Para Heroku/Render
└── README.md        # Este archivo
```

## ⚠️ Importante

- El número de Twilio debe estar configurado en modo Sandbox o Production
- El webhook de Twilio debe apuntar a la URL pública del servicio desplegado
- El servicio debe estar disponible 24/7 para recibir mensajes y enviar recordatorios

## 📞 Soporte

Para modificar las gotas o intervalos, editar `DROPS_CONFIG` en `app.py`.
