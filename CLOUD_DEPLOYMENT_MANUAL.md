# 🌐 MANUAL DE DESPLIEGUE EN LA NUBE GRATUITA Y CONEXIÓN DE CORREO

Este manual explica detalladamente cómo desplegar el **Agente Autónomo de Gestión Inteligente de Correos (`email-ai-agent`)** en un servidor en la nube **100% gratuito**, permitiendo que funcione **24/7 en segundo plano** conectándose directamente a tu correo electrónico, **sin necesidad de instalar ningún programa** en computadores corporativos o con bloqueos administrativos.

---

## 🎯 ¿Por qué Desplegar en la Nube Gratuita?

1. **Cero Instalación Local**: No requiere instalar Python, Docker, Ollama ni ningún software en la computadora restringida.
2. **Acceso desde Cualquier Navegador**: Puedes abrir el **Dashboard de Control** desde cualquier navegador web (Chrome, Edge, Firefox, celular o tablet) ingresando a un enlace HTTPS seguro (ej. `https://mi-agente-correo.onrender.com`).
3. **Funcionamiento Continuo 24/7**: El agente lee, clasifica, prioriza y responde correos de forma ininterrumpida las 24 horas del día.
4. **Costo $0 Garantizado**: Utiliza plataformas de alojamiento en la nube con capas gratuitas permanentes y servicios de IA gratuitos.

---

## 📦 OPCIÓN 1: Conexión Fácil de Correo mediante IMAP / SMTP (Recomendada)

Esta es la forma más rápida y sencilla de conectar cualquier correo electrónico (Gmail, Outlook, Yahoo o dominio corporativo) **sin descargar archivos JSON ni configurar OAuth complejo**.

### Pasos para Obtener la "Contraseña de Aplicación" en Gmail:

1. Ingresa a tu cuenta de Google y ve a **[myaccount.google.com/security](https://myaccount.google.com/security)**.
2. Asegúrate de tener activada la **Verificación en 2 pasos**.
3. En la barra de búsqueda de la cuenta de Google, escribe **"Contraseñas de aplicaciones"** (App Passwords) y selecciónala.
4. Escribe un nombre para la aplicación (ej: `Agente IA Correo`) y haz clic en **Crear**.
5. Google te entregará una **contraseña de 16 caracteres** (ej. `abcd efgh ijkl mnop`). **Cópiala y guárdala** (esta será la contraseña que usará el agente).

---

## 🤖 OPCIÓN 2: Configuración de la IA en la Nube ($0 Costo)

El agente ofrece 2 alternativas gratuitas para procesar y analizar los correos en la nube sin requerir Ollama local:

### Opción A: API Gratuita de Google Gemini ($0 Costo - Recomendada)
1. Ingresa a **[aistudio.google.com](https://aistudio.google.com)** y haz clic en **"Get API key"**.
2. Crea una clave gratuita. Google te otorga acceso de hasta 15 consultas por minuto totalmente gratis.
3. En las variables de entorno de la nube, configura:
   - `AI_PROVIDER=gemini`
   - `GEMINI_API_KEY=tu_clave_gratuita_de_gemini`

### Opción B: Motor Heurístico Autónomo ($0 Costo - Cero Claves)
- Si no deseas configurar ninguna clave de API, establece `AI_PROVIDER=heuristic`. El agente utilizará su motor semántico interno offline.

---

## 🚀 PASO A PASO: Despliegue 100% Gratuito en Render.com

[Render.com](https://render.com) es un servicio en la nube que permite alojar aplicaciones web en Python de forma gratuita.

### Paso 1: Subir el código a GitHub
1. Crea un repositorio (público o privado) en tu cuenta de [GitHub.com](https://github.com).
2. Sube la carpeta del proyecto `email-ai-agent`.

### Paso 2: Crear el Servicio Web en Render
1. Inicia sesión en **[Render.com](https://render.com)** (puedes entrar con tu cuenta de GitHub).
2. Haz clic en **New +** y selecciona **Web Service**.
3. Conecta el repositorio de GitHub de tu agente (`email-ai-agent`).

### Paso 3: Configurar los Datos del Servicio
Configura los siguientes campos:
- **Name**: `agente-correo-ia` (o el nombre que prefieras).
- **Region**: Selecciona la más cercana (ej: Oregon / Frankfurt).
- **Environment**: `Python 3`
- **Build Command**:
  ```bash
  pip install -r requirements.txt
  ```
- **Start Command**:
  ```bash
  python -m uvicorn backend.main:app --host 0.0.0.0 --port $PORT
  ```
- **Instance Type**: **Free ($0/mo)**.

### Paso 4: Cargar las Variables de Entorno (Environment Variables)
En la sección **Environment Variables** de Render, agrega los valores para tu cuenta:

| Variable | Valor de Ejemplo | Descripción |
|----------|------------------|-------------|
| `EMAIL_PROVIDER` | `imap` | Utiliza conexión IMAP/SMTP |
| `IMAP_USER` | `tucorreo@gmail.com` | Tu dirección de correo |
| `IMAP_PASSWORD` | `abcd efgh ijkl mnop` | La contraseña de 16 caracteres de Google |
| `IMAP_SERVER` | `imap.gmail.com` | Servidor IMAP |
| `IMAP_PORT` | `993` | Puerto IMAP seguro |
| `SMTP_SERVER` | `smtp.gmail.com` | Servidor SMTP |
| `SMTP_PORT` | `587` | Puerto SMTP |
| `AI_PROVIDER` | `gemini` | `gemini` o `heuristic` |
| `GEMINI_API_KEY` | `AIzaSy...` | Tu clave gratuita de Google AI Studio |
| `OPERATIONAL_MODE` | `automatic` | `automatic` (Auto-respuesta) o `supervised` (Aprobación humana) |
| `POLL_INTERVAL_MINUTES` | `2` | Intervalo de revisión (cada 2 minutos) |
| `COMPANY_NAME` | `Mi Empresa S.A.S` | Nombre institucional para respuestas |
| `AGENT_NAME` | `Asistente Virtual` | Nombre del bot |

### Paso 5: Desplegar y Disfrutar
1. Haz clic en **Create Web Service**.
2. En 2-3 minutos, Render habrá instalado el servicio y te entregará una URL HTTPS pública (ej. `https://agente-correo-ia.onrender.com`).
3. ¡Listo! Abre esa URL desde **cualquier computador restringido, tablet o teléfono móvil** para ver el Dashboard interactivo en tiempo real.

---

## 🖥️ Cómo Funciona el Uso Diario en la Computadora Restringida

```
 ┌────────────────────────────────────────────────────────┐
 │           CORREO ELECTRÓNICO (Gmail / IMAP)            │
 └───────────────────────────┬────────────────────────────┘
                             │ (Sincronización 24/7)
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │      SERVIDOR EN LA NUBE GRATUITO (Render / Koyeb)     │
 │  - Revisa correos automáticamente cada 2 minutos.      │
 │  - Analiza intención, prioriza y asigna etiquetas.     │
 │  - Responde correos simples y seguros.                 │
 │  - Deriva casos financieros/legales a revisión.        │
 └───────────────────────────┬────────────────────────────┘
                             │ (Acceso mediante URL)
                             ▼
 ┌────────────────────────────────────────────────────────┐
 │  CUALQUIER COMPUTADORA RESTRINGIDA / CELULAR / TABLET  │
 │  - Abre https://agente-correo-ia.onrender.com          │
 │  - Revisa contadores, estadísticas y respuestas.      │
 │  - Aprueba respuestas pendientes con 1 clic.           │
 └───────────────────────────┬────────────────────────────┘
```

1. **Cero Mantenimiento**: No necesitas dejar ninguna computadora encendida. El servidor en la nube trabaja continuamente.
2. **Revisión Humana desde la Web**: Si llega un correo de alto riesgo (contratos, reclamos graves, cotizaciones o datos bancarios), aparecerá en la pestaña **"Revisión Humana"** del Dashboard.
3. **Aprobar con 1 Clic**: Simplemente abres el enlace del Dashboard desde el computador restringido, lees el borrador sugerido por la IA y haces clic en **"Aprobar & Enviar Respuesta"**.
