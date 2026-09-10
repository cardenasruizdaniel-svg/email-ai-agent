# 🤖 Agente Autónomo de Gestión Inteligente de Correos (`email-ai-agent`)

Una aplicación y agente de inteligencia artificial **100 % autónomo, gratuito y de código abierto** para gestionar automáticamente cuentas de correo electrónico (Gmail o IMAP/SMTP). El sistema analiza, clasifica, etiqueta, prioriza, relaciona conversaciones anteriores y responde mensajes de bajo riesgo con cero alucinación, enrutando correos complejos o financieros a revisión humana.

---

## 🚀 Características Principales

- **Costo $0 Garantizado**: Integración con **Ollama** y modelos de código abierto (`llama3:8b`, `qwen2.5:7b`, `mistral`), con motor heurístico local de respaldo sin costo ni dependencias de pago.
- **Conexión Dual Gmail & IMAP**: Soporte nativo para **Gmail API (OAuth2)**, servidores **IMAP/SMTP** genéricos y un **Mock Email Engine** para pruebas fuera de línea.
- **Sistema Inteligente de Etiquetas**: Etiquetado reutilizable sin saturación (`Información relevante`, `Respuesta automática`, `Solicitud`, `Urgente`, `Revisión humana`, `Respondido por IA`, `Spam`).
- **Capa Estricta Anti-Alucinación & Matriz de Riesgo**: Bloqueo automático de respuestas en correos que involucren contratos, transferencias bancarias, finanzas, disputas legales o baja confianza (<85%).
- **Memoria de Remitentes e Hilos de Conversación**: Almacenamiento continuo en SQLite con seguimiento de empresas, temas frecuentes e historial de interacciones.
- **Motor de Reglas Personalizables**: Definición de condiciones SI -> ENTONCES para prioridades, etiquetas y overrides.
- **Ejecución 24/7 en la Nube Gratuita ($0)**: Se puede desplegar en **Render, Koyeb o Hugging Face** en 5 minutos para funcionar 24/7 **sin instalar ningún programa** en computadores corporativos restringidos.
- **Acceso desde Cualquier Navegador**: Panel de control accesible mediante URL HTTPS desde computadores restringidos, celulares o tablets.

---

## 📂 Estructura del Proyecto

```text
email-ai-agent/
│
├── backend/
│   ├── email_client/     # Conectores Gmail API, IMAP y Mock Client
│   ├── services/         # Decision Engine, Rule Engine, Dispatcher, Scheduler
│   └── main.py           # Servidor REST API FastAPI y servidor de archivos estáticos
├── frontend/             # Dashboard SPA (HTML5, Tailwind CSS, JavaScript Vanilla)
├── ai/                   # Motor de IA (Ollama, Prompts, Extractor PDF)
├── database/             # Modelos SQLAlchemy, Conexión Async SQLite y Repositorio
├── config/               # Configuración centralizada de Pydantic (.env)
├── logs/                 # Registros de actividad y auditoría
├── tests/                # Suite de pruebas automatizadas con 12 escenarios de prueba
├── .env.example          # Plantilla de variables de entorno
├── requirements.txt      # Dependencias de Python
├── Dockerfile            # Imagen Docker de la aplicación
├── docker-compose.yml    # Orquestación Docker para App + Ollama
└── README.md             # Guía completa de uso y configuración
```

---

## 🛠️ Guía de Instalación y Configuración

### 1. Instalación de Requisitos Locales

```bash
cd email-ai-agent
python -m venv venv
# En Windows:
venv\Scripts\activate
# En Linux/macOS:
source venv/bin/activate

pip install -r requirements.txt
```

---

### 2. Instalación y Configuración de Ollama (IA Gratuita)

1. Descarga e instala **Ollama** desde [ollama.com](https://ollama.com).
2. Inicia el servicio de Ollama en tu terminal:
   ```bash
   ollama serve
   ```
3. Descarga el modelo de IA recomendado (ejemplo Llama 3 8B o Qwen 2.5):
   ```bash
   ollama pull llama3:8b
   ```
*(Nota: Si no instalas Ollama, el agente utilizará automáticamente su motor heurístico local sin interrumpir el funcionamiento).*

---

### 3. Configuración de Variables de Entorno (`.env`)

Copia la plantilla `.env.example` a `.env`:
```bash
cp .env.example .env
```

Parámetros clave en `.env`:
```ini
OPERATIONAL_MODE=automatic       # automatic | supervised
POLL_INTERVAL_MINUTES=2          # Intervalo de lectura continua (1-5 min)
AI_PROVIDER=ollama               # ollama | mock | gemini | openai
OLLAMA_MODEL=llama3:8b
EMAIL_PROVIDER=mock              # mock | gmail | imap
COMPANY_NAME=Empresa ABC
AGENT_NAME=Asistente Virtual IA
```

---

### 4. Configurar Gmail API y Credenciales OAuth2

Para conectar tu cuenta real de Gmail:

1. Ve a [Google Cloud Console](https://console.cloud.google.com/).
2. Crea un proyecto y habilita la **Gmail API**.
3. En **Pantalla de consentimiento de OAuth**, selecciona *Usuario externo* y agrega el alcance: `https://www.googleapis.com/auth/gmail.modify`.
4. En **Credenciales**, crea un ID de cliente OAuth 2.0 de tipo *Aplicación de escritorio*.
5. Descarga el JSON y guárdalo en `email-ai-agent/config/credentials.json`.
6. En `.env`, establece:
   ```ini
   EMAIL_PROVIDER=gmail
   ```
7. Al ejecutar por primera vez, se abrirá el navegador para autorizar y se creará `config/token.json`.

---

### 5. Cómo Iniciar el Sistema

Ejecuta el servidor FastAPI con Uvicorn:

```bash
python -m uvicorn backend.main:app --reload --port 8005
```

Abre tu navegador en:
👉 **`http://localhost:8005`** para acceder al Dashboard Web.

---

### 6. Configurar Etiquetas y Respuestas Automáticas

El sistema crea y asigna automáticamente etiquetas sin duplicarlas:
- `Información relevante`: Para solicitudes de información o tarifas.
- `Respuesta automática`: Para confirmaciones simples (Recibido, Sí, Disponible).
- `Solicitud`: Para solicitudes de cotización o documentos.
- `Urgente`: Asunto con fallas o vencimientos críticos.
- `Revisión humana`: Mensajes ambiguos, financieros o contractuales.
- `Respondido por IA`: Correos contestados automáticamente.

Las plantillas de respuesta se adaptan con la información corporativa configurada en tu archivo `.env`.

---

### 7. Cambiar entre Modo Automático y Modo Supervisado

Puedes alternar el modo desde el **Dashboard Web** en la parte superior derecha o desde la API:
- **Modo Automático (⚡)**: La IA responde automáticamente los correos seguros (>95% confianza y riesgo bajo).
- **Modo Supervisado (👁️)**: La IA genera el borrador de respuesta, pero **requiere aprobación humana** en la pestaña *Revisión Humana* antes de enviar.

---

### 8. Cómo Realizar Pruebas Automatizadas

El proyecto incluye una suite completa con 12 escenarios reales de correo (solicitud de información, confirmación simple, cotizaciones complejas, queja urgente, fraude/bancario, spam, ambiguo, adjuntos PDF y seguimiento).

Para ejecutar los tests:
```bash
pytest tests/ -v
```

---

## 🐳 Ejecución con Docker Compose

Si prefieres ejecutar todo mediante contenedores Docker (App + Ollama):

```bash
docker-compose up --build
```
El panel estará disponible en `http://localhost:8005`.
