#!/bin/bash
# ==============================================================================
# Script de Ejecución Rápida para iMac / macOS - Email AI Agent
# ==============================================================================

set -e

echo "🍏 Iniciando Agente de Correo IA en iMac (macOS)..."

# 1. Verificar Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 no está instalado. Por favor instala Python 3 desde python.org o usando Homebrew."
    exit 1
fi

echo "🐍 Python detectado: $(python3 --version)"

# 2. Crear entorno virtual si no existe
if [ ! -d "venv" ]; then
    echo "📦 Creando entorno virtual (venv)..."
    python3 -m venv venv
fi

# 3. Activar entorno virtual e instalar dependencias
echo "⚡ Activando entorno virtual e instalando dependencias..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Crear archivo .env si no existe (SQLite local listo para pruebas inmediatas a costo $0)
if [ ! -f ".env" ]; then
    echo "⚙️ Creando archivo de configuración inicial (.env)..."
    cat <<EOT > .env
OPERATIONAL_MODE=automatic
POLL_INTERVAL_MINUTES=2
AI_PROVIDER=heuristic
EMAIL_PROVIDER=mock
COMPANY_NAME=Clínica Central
AGENT_NAME=Asistente Virtual IA
SUPERVISOR_EMAIL=coordinacion@clinica.com
EOT
fi

# 5. Obtener IP local del iMac en la red
IP_LOCAL=$(ipconfig getifaddr en0 2>/dev/null || ipconfig getifaddr en1 2>/dev/null || echo "localhost")

echo ""
echo "================================================================="
echo "🎉 ¡Agente listo para operar en tu iMac!"
echo "📍 Acceso desde tu iMac:      http://localhost:8005"
echo "🌐 Acceso desde otros equipos: http://${IP_LOCAL}:8005"
echo "================================================================="
echo ""
echo "Iniciando servidor (Presiona CTRL+C para detener)..."

uvicorn backend.main:app --host 0.0.0.0 --port 8005 --reload
