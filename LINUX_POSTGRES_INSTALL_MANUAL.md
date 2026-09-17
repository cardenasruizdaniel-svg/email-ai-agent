# 🐧 MANUAL DE INSTALACIÓN Y GESTIÓN EN LINUX CON POSTGRESQL

Este manual guía paso a paso la instalación, configuración y gestión continua del **Agente Autónomo de Gestión Inteligente de Correos (`email-ai-agent`)** en servidores **Linux** (Ubuntu, Debian, RHEL, CentOS) utilizando **PostgreSQL** como base de datos de producción y **systemd** para ejecución 24/7 en segundo plano.

---

## 📋 Requisitos Previos en el Servidor Linux

- Sistema Operativo: Ubuntu 20.04/22.04/24.04 LTS, Debian 11/12, CentOS/RHEL 8/9.
- Acceso con privilegios `sudo` o `root`.
- Python 3.10+ instalado.
- Servidor PostgreSQL instalado y en ejecución.

---

## ⚡ OPCIÓN A: Instalación Automática mediante Script Bash (Recomendada)

Hemos incluido el script `setup_linux.sh` que realiza toda la instalación de paquetes, creación de la base de datos PostgreSQL, entorno virtual de Python y servicio de systemd en menos de 2 minutos:

```bash
cd email-ai-agent
chmod +x setup_linux.sh
./setup_linux.sh
```

---

## 🛠️ OPCIÓN B: Instalación Manual Paso a Paso

### 1. Instalación de Dependencias del Sistema
En Ubuntu/Debian:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip postgresql postgresql-contrib git
```

En RHEL/CentOS/Rocky Linux:
```bash
sudo dnf install -y python3 python3-pip postgresql-server postgresql-contrib git
sudo postgresql-setup --initdb
sudo systemctl enable --now postgresql
```

---

### 2. Configurar Base de Datos PostgreSQL
Accede a la consola de PostgreSQL y crea la base de datos y usuario:

```bash
sudo -u postgres psql
```

Dentro de la consola SQL de Postgres:
```sql
CREATE DATABASE email_agent_db;
CREATE USER email_user WITH PASSWORD 'EmailAgentPass2026!';
GRANT ALL PRIVILEGES ON DATABASE email_agent_db TO email_user;
GRANT ALL ON SCHEMA public TO email_user;
\q
```

---

### 3. Configurar Entorno Virtual de Python y Dependencias
Dentro del directorio del proyecto:

```bash
cd email-ai-agent
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

---

### 4. Configurar Variables de Entorno (`.env`)
Crea o edita tu archivo `.env` configurando la cadena de conexión a PostgreSQL:

```ini
OPERATIONAL_MODE=automatic
POLL_INTERVAL_MINUTES=2
AI_PROVIDER=heuristic
EMAIL_PROVIDER=mock
COMPANY_NAME=Empresa Linux S.A.S
AGENT_NAME=Asistente Virtual IA

# Conexión a PostgreSQL (Driver asyncpg)
DATABASE_URL=postgresql+asyncpg://email_user:EmailAgentPass2026!@localhost:5432/email_agent_db
```

---

### 5. Configurar Servicio systemd (Ejecución 24/7 en Linux)
Para que la aplicación se inicie automáticamente con el sistema y se mantenga en ejecución 24/7 en segundo plano:

1. Crea el archivo de servicio `/etc/systemd/system/email-agent.service`:

```bash
sudo nano /etc/systemd/system/email-agent.service
```

2. Pega el siguiente contenido (reemplaza `/ruta/a/email-ai-agent` y `tu_usuario` por los reales):

```ini
[Unit]
Description=Servicio Agente Autonomo de Gestion de Correos IA
After=network.target postgresql.service

[Service]
User=tu_usuario
WorkingDirectory=/ruta/a/email-ai-agent
ExecStart=/ruta/a/email-ai-agent/venv/bin/python -m uvicorn backend.main:app --host 0.0.0.0 --port 8005
Restart=always
RestartSec=5
Environment=PATH=/ruta/a/email-ai-agent/venv/bin:/usr/bin:/bin

[Install]
WantedBy=multi-user.target
```

3. Habilita e inicia el servicio:
```bash
sudo systemctl daemon-reload
sudo systemctl enable email-agent
sudo systemctl start email-agent
```

---

## 🛠️ Comandos de Gestión del Servicio en Linux

| Acción | Comando |
|---|---|
| **Ver estado del servicio** | `sudo systemctl status email-agent` |
| **Iniciar servicio** | `sudo systemctl start email-agent` |
| **Detener servicio** | `sudo systemctl stop email-agent` |
| **Reiniciar servicio** | `sudo systemctl restart email-agent` |
| **Ver logs en tiempo real** | `sudo journalctl -u email-agent -f` |

---

## 🌐 Acceso al Dashboard Web desde Linux o Red Local

Abre cualquier navegador web ingresando a:
👉 **`http://IP_DE_TU_SERVIDOR_LINUX:8005`**

Desde la nueva pestaña **`⚙️ Configuración del Sistema`** en el Dashboard, podrás cambiar en cualquier momento:
- La cuenta de correo gestionada (Gmail, Office 365, Sura, IMAP).
- La clave o proveedor de IA (Google Gemini $0, Motor Heurístico $0, Ollama).
- El modo operativo (Automático o Supervisado).
- La firma y nombre institucional.
