#!/bin/bash
# ==============================================================================
# Script de Instalación Automatizada para Linux (Ubuntu/Debian) - Email AI Agent
# ==============================================================================

set -e

echo "🚀 Iniciando instalación de Email AI Agent en Linux..."

# 1. Actualizar repositorios e instalar paquetes del sistema
echo "📦 Instalando dependencias del sistema y PostgreSQL..."
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib git

# 2. Configurar Base de Datos PostgreSQL
DB_NAME="email_agent_db"
DB_USER="email_user"
DB_PASS="EmailAgentPass2026!"

echo "🐘 Configurando base de datos PostgreSQL: $DB_NAME..."
sudo -u postgres psql -c "CREATE DATABASE $DB_NAME;" 2>/dev/null || echo "Base de datos ya existe."
sudo -u postgres psql -c "CREATE USER $DB_USER WITH PASSWORD '$DB_PASS';" 2>/dev/null || echo "Usuario ya existe."
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE $DB_NAME TO $DB_USER;"
sudo -u postgres psql -d $DB_NAME -c "GRANT ALL ON SCHEMA public TO $DB_USER;" 2>/dev/null || true

# 3. Crear entorno virtual e instalar requerimientos
echo "🐍 Configurando entorno virtual Python..."
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 4. Crear archivo .env preconfigurado para Linux + PostgreSQL
if [ ! -f .env ]; then
    echo "⚙️ Creando archivo .env con conexión a PostgreSQL..."
    cat <<EOT > .env
OPERATIONAL_MODE=automatic
POLL_INTERVAL_MINUTES=2
AI_PROVIDER=heuristic
EMAIL_PROVIDER=mock
COMPANY_NAME=Empresa Linux S.A.S
AGENT_NAME=Asistente Virtual IA
DATABASE_URL=postgresql+asyncpg://$DB_USER:$DB_PASS@localhost:5432/$DB_NAME
EOT
fi

# 5. Configurar servicio systemd para ejecución 24/7 en segundo plano
SERVICE_PATH="/etc/systemd/system/email-agent.service"
WORKING_DIR=$(pwd)
USER_NAME=$(whoami)

echo "🔧 Creando servicio systemd ($SERVICE_PATH)..."
sudo bash -c "cat <<EOT > $SERVICE_PATH
[Unit]
Description=Servicio Agente Autonomo de Gestion de Correos IA
After=network.target postgresql.service

[Service]
User=$USER_NAME
WorkingDirectory=$WORKING_DIR
ExecStart=$WORKING_DIR/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8005
Restart=always
RestartSec=5
Environment=PATH=$WORKING_DIR/venv/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
EOT"

# 6. Recargar systemd y activar servicio
echo "🔄 Recargando e iniciando servicio systemd..."
sudo systemctl daemon-reload
sudo systemctl enable email-agent
sudo systemctl restart email-agent

echo "=================================================================="
echo "✅ ¡Instalación en Linux completada exitosamente!"
echo "------------------------------------------------------------------"
echo "🌐 Dashboard disponible en: http://localhost:8005 (o IP de tu servidor)"
echo "📊 Ver estado del servicio: sudo systemctl status email-agent"
echo "📜 Ver logs en tiempo real: sudo journalctl -u email-agent -f"
echo "=================================================================="
