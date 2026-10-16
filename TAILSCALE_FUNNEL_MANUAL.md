# 🌐 Guía de Despliegue con Tailscale Funnel en iMac (macOS)

**Tailscale Funnel** permite exponer tu Agente de Correos que corre localmente en el iMac (puerto `8005`) hacia Internet de forma pública, segura y con certificado **HTTPS automático**.

> **Ventaja Principal**:  
> **Cualquier usuario o dispositivo (computadores de la clínica, celulares, etc.) puede entrar desde cualquier lugar mediante un enlace web público, SIN necesidad de tener Tailscale instalado ni pertenecer a tu red VPN**.

---

## 📋 Requisitos Previos

1. **Tener una cuenta gratuita de Tailscale**: [tailscale.com](https://tailscale.com).
2. **Tener Tailscale instalado en el iMac**:
   - Descárgalo de la Mac App Store o desde la terminal con Homebrew:
     ```bash
     brew install tailscale
     ```
   - O usando la app oficial: [Descargar Tailscale para macOS](https://tailscale.com/download/mac).

---

## 🚀 Paso a Paso: Activación y Publicación

### 1. Activar permisos de Funnel en el panel de Tailscale (Solo 1 vez)
1. Ve al panel de administración: [login.tailscale.com/admin/acls](https://login.tailscale.com/admin/acls).
2. En la sección **Access Controls (ACL)**, asegúrate de que tu usuario tenga permiso para Funnel agregando el atributo `funnel`:
   ```json
   "nodeAttrs": [
       {
           "target": ["autogroup:members"],
           "attr": ["funnel"]
       }
   ]
   ```
   *(Nota: Si ejecutas el comando del paso 3 por primera vez sin esto, la terminal de Tailscale te dará un enlace directo para habilitarlo con un solo clic).*

---

### 2. Encender el Agente de Correo en el iMac
En una terminal del iMac dentro de la carpeta del proyecto:
```bash
./run_mac.sh
```
*(Esto iniciará el servidor en `http://localhost:8005`)*.

---

### 3. Exponer el Puerto 8005 con Tailscale Funnel
Abre una **segunda pestaña o ventana de la Terminal** en el iMac y ejecuta:

```bash
tailscale funnel 8005
```

> 💡 **Si tienes la aplicación gráfica de macOS instalada**, el ejecutable CLI de Tailscale se encuentra en:
> ```bash
> /Applications/Tailscale.app/Contents/MacOS/Tailscale funnel 8005
> ```
> O puedes crear el alias rápido:
> ```bash
> alias tailscale="/Applications/Tailscale.app/Contents/MacOS/Tailscale"
> tailscale funnel 8005
> ```

---

### 4. Obtener tu URL Pública HTTPS
Al ejecutar el comando, Tailscale te mostrará tu enlace público seguro:

```text
Available on the internet:

https://tu-imac.tu-tailnet.ts.net/
|-- proxies to http://127.0.0.1:8005
```

Para verificar el estado o ver tu URL en cualquier momento:
```bash
tailscale funnel status
```

---

### 5. Probar desde cualquier dispositivo (Sin Tailscale)
1. Toma tu celular (incluso con datos móviles 4G/5G, desconectado del WiFi y sin app de Tailscale).
2. Abre Safari o Chrome y navega a:
   **`https://tu-imac.tu-tailnet.ts.net`**
3. Verás la plataforma del Agente de Correo cargada completamente con HTTPS seguro:
   - Podrás ver la **Bandeja de Correos**.
   - Podrás gestionar la **Trazabilidad de Casos**.
   - Podrás revisar los **Cuellos de Botella** y aprobar/rechazar solicitudes.

---

## 🛠️ Comandos Útiles de Administración

| Acción | Comando |
| :--- | :--- |
| **Ver estado del Funnel** | `tailscale funnel status` |
| **Desactivar temporalmente** | `tailscale funnel --bg 8005 off` |
| **Volver a activar en segundo plano** | `tailscale funnel --bg 8005` |
| **Ver nombre de tu nodo** | `tailscale status` |
