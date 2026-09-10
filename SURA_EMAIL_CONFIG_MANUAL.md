# 📧 MANUAL DE CONFIGURACIÓN DE CORREO SURA EN RENDER

Este manual explica exactamente cómo y dónde ingresar las credenciales del correo **`lagaviria@sura.com.co`** en la plataforma **Render.com** para que el Agente comience a leer, clasificar y gestionar los correos de tu bandeja de entrada en tiempo real.

---

## 📌 ¿Dónde se Configuran las Credenciales en Render?

Las credenciales no se escriben directamente dentro del código público por seguridad; se ingresan en la sección **Environment (Variables de Entorno)** de tu panel de **Render.com**.

### Pasos para Ingresar a las Variables en Render:

1. Entra a tu panel de **[dashboard.render.com](https://dashboard.render.com)**.
2. Haz clic sobre tu servicio activo llamado **`agente-correo-ia`**.
3. En el menú lateral izquierdo, haz clic en **`Environment`** (Variables de Entorno).
4. Haz clic en el botón **`Add Environment Variable`** (o **`Edit Variables`**).

---

## 📋 Lista Exacta de Variables a Copiar y Pegar para SURA

Copia y pega cada **Nombre (Key)** y **Valor (Value)** en el panel de Render:

| Key (Nombre de Variable) | Value (Valor Exacto) | Descripción |
|---|---|---|
| `EMAIL_PROVIDER` | `imap` | Activa la lectura real por IMAP/SMTP |
| `IMAP_USER` | `lagaviria@sura.com.co` | Tu cuenta de correo corporativa Sura |
| `IMAP_PASSWORD` | `Lag1094894814**` | Tu contraseña de acceso |
| `IMAP_SERVER` | `outlook.office365.com` | Servidor IMAP de Microsoft/Office365 Sura |
| `IMAP_PORT` | `993` | Puerto IMAP seguro (SSL) |
| `SMTP_SERVER` | `smtp.office365.com` | Servidor de salida SMTP |
| `SMTP_PORT` | `587` | Puerto SMTP seguro (TLS) |
| `AI_PROVIDER` | `heuristic` | `heuristic` (Procesamiento gratis sin claves) o `gemini` |
| `OPERATIONAL_MODE` | `automatic` | `automatic` (Auto-responder) o `supervised` (Aprobación humana) |
| `COMPANY_NAME` | `Sura` | Nombre de la empresa para firmas |
| `AGENT_NAME` | `Asistente Virtual` | Nombre del gestor |

---

## 🔄 ¿Cómo Aplicar los Cambios y Probar?

1. Una vez agregadas todas las variables en Render, haz clic en **`Save Changes`** (Guardar Cambios).
2. Render reiniciará automáticamente tu servicio en 30 segundos para cargar los nuevos datos.
3. Abre tu Dashboard en:  
   👉 **`https://agente-correo-ia.onrender.com`**
4. Haz clic en el botón superior derecho: **`Sincronizar Correos`**.
