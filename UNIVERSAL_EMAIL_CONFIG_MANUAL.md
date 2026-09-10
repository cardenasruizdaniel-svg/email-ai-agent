# ⚙️ MANUAL COMPLETO Y UNIVERSAL DE CONFIGURACIÓN DESDE LA PLATAFORMA

Este manual explica cómo configurar y modificar en cualquier momento **cualquier cuenta de correo electrónico** (Gmail, Outlook/Office365, Sura, Yahoo o Servidores Corporativos IMAP/SMTP) y motor de Inteligencia Artificial directamente desde el nuevo panel de **Configuración del Sistema** en tu Dashboard Web, **sin necesidad de entrar a Render ni editar archivos de código**.

---

## 🎯 ¿Cómo Acceder al Panel de Configuración en el Dashboard?

1. Abre tu Dashboard Web en el navegador:  
   👉 **`https://agente-correo-ia.onrender.com`** (o tu servidor local).
2. En la barra de pestañas superior, haz clic en la nueva opción destacada:  
   ⚙️ **`Configuración del Sistema`**.

Ahí encontrarás 3 secciones interactivas para modificar cualquier dato en tiempo real.

---

## 📋 SECCIÓN 1: Configurar Cualquier Cuenta de Correo (IMAP / SMTP)

El panel incluye presets automáticos para autocompletar servidores según el proveedor que elijas:

### Presets Disponibles:
1. **Gmail**:
   - Presiona la opción `Gmail` en el selector de presets.
   - Servidores configurados automáticamente: `imap.gmail.com` (Puerto 993) y `smtp.gmail.com` (Puerto 587).
   - **Requisito**: Debes usar una **Contraseña de Aplicación de 16 caracteres** obtenida desde `myaccount.google.com/security`.

2. **Outlook / Office 365 / Sura (Reenvío a Gmail)**:
   - Presiona la opción `Outlook / Office 365`.
   - Servidores configurados automáticamente: `outlook.office365.com` (Puerto 993) y `smtp.office365.com` (Puerto 587).

3. **Yahoo Mail**:
   - Servidores: `imap.mail.yahoo.com` (993) y `smtp.mail.yahoo.com` (587).

4. **Personalizado (Servidor propio o Hosting empresarial)**:
   - Ingresa manualmente el servidor IMAP y SMTP de tu proveedor cPanel, Zimbra o Exchange.

### Campos a Diligenciar:
- **Correo Electrónico (IMAP User)**: Tu dirección de correo completa (ej: `micorreo@gmail.com`).
- **Contraseña**: Tu clave de acceso o contraseña de aplicación de 16 caracteres.
- **Servidor IMAP Entrante**: `imap.gmail.com` u `outlook.office365.com`.
- **Servidor SMTP Saliente**: `smtp.gmail.com` u `smtp.office365.com`.

---

## 🤖 SECCIÓN 2: Configurar la Inteligencia Artificial ($0 Costo)

Puedes alternar entre 3 motores de Inteligencia Artificial según tus preferencias:

1. **Google Gemini API Gratuita ($0 - Recomendado)**:
   - Selecciona `Google Gemini API Gratuita`.
   - Ingresa tu clave gratuita obtenida en **[aistudio.google.com](https://aistudio.google.com)**.
   - Ofrece el procesamiento de texto e intención más rápido y sofisticado sin costo.

2. **Motor Heurístico Autónomo ($0 - Sin Claves)**:
   - Selecciona `Motor Heurístico Autónomo`.
   - No requiere ninguna clave externa. Analiza la intención semántica por reglas lógicas internas.

3. **Ollama Local**:
   - Para instalaciones locales en servidores propios que tengan Ollama corriendo (`http://localhost:11434`).

---

## 🏢 SECCIÓN 3: Identidad Corporativa & Modo de Operación

- **Modo Operativo**:
  - `⚡ Automático`: El agente clasifica, prioriza y responde automáticamente correos de bajo riesgo (>95% confianza).
  - `👁️ Supervisado`: El agente genera los borradores de respuesta pero los envía a la pestaña *Revisión Humana* para aprobación manual antes de enviar.
- **Nombre de la Empresa**: Ejemplo: `Sura` o `Mi Empresa S.A.S`.
- **Nombre del Asistente Virtual**: Ejemplo: `Asistente de Atención al Cliente`.
- **Firma de Correos Salientes**: Texto de despedida institucional para todos los correos automáticos.

---

## 💾 ¿Cómo Guardar y Aplicar los Cambios?

Una vez diligenciados o modificados tus datos:

1. Haz clic en el botón verde inferior: **`Guardar Configuración e Iniciar Sincronización`**.
2. El sistema guardará los cambios inmediatamente en memoria y actualizará tu archivo de entorno.
3. El agente ejecutará una sincronización instantánea para probar la conexión con el nuevo correo y comenzar a gestionar la bandeja de entrada.
