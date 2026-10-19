# Manual Operativo y Guía Técnica del Sistema PADO Agudo
## HomeCare del Quindío I.P.S. — Trazabilidad Asistencial con IA

---

## 1. Presentación y Propósito Institucional

Este sistema automatiza la recepción, análisis clínico con Inteligencia Artificial, asignación departamental y trazabilidad integral del **Programa de Atención Domiciliaria del Paciente Agudo (PADO Agudo)** para **HomeCare del Quindío I.P.S.**

El objetivo principal es eliminar los cuellos de botella en la radicación de solicitudes, garantizar que ningún paciente quede sin asignación y asegurar que cada departamento (Atención al Usuario, Inventarios, Facturación y Asistencial) ejecute sus funciones con exactitud y en los tiempos requeridos.

---

## 2. Directorio de Usuarios y Roles Oficiales

El sistema cuenta con cuentas dedicadas para cada uno de los responsables definidos en el flujo oficial de HomeCare del Quindío:

| Usuario | Nombre Completo | Departamento | Rol y Responsabilidad Principal |
| :--- | :--- | :--- | :--- |
| `carolina` | **Carolina Venencia** | 🟣 Atención al Usuario | Recibe solicitud inicial por correo, apertura caso PADO, verifica requisitos y envía correo de aceptación/rechazo al remitente. |
| `german` | **German Giraldo** | 🟢 Inventarios | Verifica insumos/medicamentos contratados, genera órdenes de compra a proveedores, alista dotación de insumos y recibe reintegros. |
| `esteban` | **Esteban Gacha** | 🔴 Facturación | Verifica copagos, valida afiliación en EPS, ingresa paciente al censo diario (Secretaría de Salud y EPS) y factura el servicio. |
| `hernando` | **Dr. Hernando Vence** | 🔵 Asistencial | Valoración integral presencial (egreso clínica) o telefónica (ambulatorio), historia clínica de ingreso, consentimiento informado y visita médica de egreso. |
| `federico` | **Dr. Federico Cortes** | 🔵 Asistencial | Coordinación PADO, confirmación de horarios, aceptación/rechazo técnico, definición de extensiones y cobro de copagos. |
| `franchesca` | **Franchesca Triviño** | 🟣 Atención al Usuario | Contacta al paciente/cuidador tras aceptación médica, crea al paciente en Medifolios y lo asigna en cuadros de aplicadores. |
| `yurli` | **Yurli** | 🟣 Atención al Usuario | Monitorea la continuidad y aplicación de medicamentos; gestiona la salida del paciente en el módulo de hospitalización. |
| `admin` | **Administrador / Coordinación** | 🛡️ Dirección General | Control maestro de configuración, supervisión de cuellos de botella, métricas KPI y auditoría. |

> [!NOTE]
> **Contraseña por defecto para todas las cuentas iniciales**: `ips123456` *(se recomienda cambiarla en el primer inicio de sesión)*.
> Todas las cuentas tienen el estado **ACTIVO** y los datos persistentes de la base de datos están protegidos contra reinicios o actualizaciones.

---

## 3. Diagrama de Flujo Oficial PADO Agudo

El siguiente diagrama refleja fielmente el flujo institucional establecido por HomeCare del Quindío I.P.S.:

```mermaid
flowchart TD
    %% Estilos por departamento
    classDef depUser fill:#7c3aed,stroke:#5b21b6,color:#ffffff,stroke-width:2px;
    classDef depInv fill:#15803d,stroke:#166534,color:#ffffff,stroke-width:2px;
    classDef depFact fill:#be123c,stroke:#9f1239,color:#ffffff,stroke-width:2px;
    classDef depAsist fill:#0369a1,stroke:#075985,color:#ffffff,stroke-width:2px;
    classDef decision fill:#f59e0b,stroke:#d97706,color:#000000,stroke-width:2px;

    Start([Inicio: Correo Solicitud Remitente]) --> Step1[Carolina Venencia: Recibe solicitud y verifica requisitos]::depUser
    
    Step1 --> ParFork{Revisión Simultánea}
    
    ParFork -->|Inventarios| Step2[German Giraldo: Verifica insumos y medicamentos contratados]::depInv
    Step2 --> Step2B[German Giraldo: Genera orden de compra a proveedores]::depInv
    
    ParFork -->|Facturación| Step3[Esteban Gacha: Verifica copago y afiliación en EPS]::depFact
    
    Step2B --> Join1[Consolidación Técnica]
    Step3 --> Join1
    
    Join1 --> TriageOrig{¿Origen del Paciente?}:::decision
    
    TriageOrig -->|Egreso Clínica / Hospital| Step4A[Dr. Hernando Vence: Valoración Integral Presencial]::depAsist
    TriageOrig -->|Paciente Ambulatorio| Step4B[Dr. Hernando Vence: Valoración Médica Telefónica]::depAsist
    
    Step4A --> Step4C[Dr. Hernando Vence: Historia Clínica Ingreso y Consentimiento Informado]::depAsist
    Step4B --> Step4C
    
    Step4C --> Step5[Dr. Federico Cortes: Coordinación PADO y Confirmación de Horarios]::depAsist
    
    Step5 --> DecAcepta{¿Aceptación del Caso?}:::decision
    
    DecAcepta -->|NO Rechazado| Step6Rech[Carolina Venencia: Envía correo de NO aceptación con justificación clínica]::depUser
    Step6Rech --> FinRech([Fin del Proceso - Rechazado])
    
    DecAcepta -->|SÍ Aceptado| Step6Acept[Carolina Venencia: Envía correo de aceptación formal]::depUser
    
    Step6Acept --> Step7[Franchesca Triviño: Contacta paciente y crea en plataforma Medifolios]::depUser
    Step7 --> Step7B[Franchesca Triviño: Asigna paciente en cuadro de aplicadores]::depUser
    
    Step7B --> Step8[German Giraldo: Alistamiento de Insumos según Días de Tratamiento]::depInv
    
    Step8 --> Step9[Esteban Gacha: Ingreso a Censo Diario Secretaría de Salud y EPS]::depFact
    
    Step9 --> Step10[Yurli: Monitoreo de aplicaciones y salida en Módulo de Hospitalización]::depUser
    
    Step10 --> Step11[Dr. Hernando Vence: Visita Médica de Egreso]::depAsist
    Step11 --> Step12[German Giraldo: Reintegro y devolución de insumos sobrantes]::depInv
    Step12 --> Step13[Esteban Gacha: Facturación y Cobro de Copago por Extensiones]::depFact
    
    Step13 --> FinExito([Fin del Proceso PADO - Paciente de Alta])
```

---

## 4. Guía Operativa Paso a Paso

### Paso 1: Recepción y Radicación Inicial (Atención al Usuario)
- **Responsable**: `carolina` (Carolina Venencia).
- **Acción**: El sistema de IA monitorea automáticamente la bandeja de entrada. Al ingresar un correo con órdenes o solicitudes médicas:
  - Extrae nombre del paciente, documento de identidad, EPS de afiliación y medicamentos prescritos.
  - Genera el caso con código único de trazabilidad (ej: `CASO-2026-0012`).
  - Carolina revisa que la documentación esté completa (orden médica, fórmula y resumen de historia clínica).

### Paso 2: Verificación de Insumos y Órdenes de Compra (Inventarios)
- **Responsable**: `german` (German Giraldo).
- **Acción**: German valida en el sistema que los medicamentos y dispositivos prescritos se encuentren en el convenio de la EPS. Si no hay stock inmediato, genera la orden de compra a proveedores autorizados.

### Paso 3: Validación de Copagos y Afiliación EPS (Facturación)
- **Responsable**: `esteban` (Esteban Gacha).
- **Acción**: Esteban verifica en la base de datos de BDUA/ADRES y la EPS que el usuario se encuentre activo en el régimen correspondiente y liquida el valor del copago o cuota moderadora según categoría.

### Paso 4: Triage Médico y Valoración de Ingreso (Asistencial)
- **Responsable**: `hernando` (Dr. Hernando Vence).
- **Condición según Origen**:
  - **Si proviene de Clínica u Hospital (Egreso)**: El Dr. Hernando Vence se desplaza a realizar la **valoración integral presencial**.
  - **Si proviene de Consulta Externa / Domicilio (Ambulatorio)**: Realiza la **valoración médica telefónica** para verificar condiciones de ingreso.
- Diligencia la historia clínica de apertura y obtiene el consentimiento informado firmado por el paciente o familiar.

### Paso 5: Coordinación Médica y Aceptación/Rechazo (Asistencial)
- **Responsable**: `federico` (Dr. Federico Cortes).
- **Acción**: El Dr. Federico analiza los horarios prescritos (ej: c/8h, c/12h, c/24h) y la cobertura geográfica del aplicador:
  - **Si es Aceptado**: Coordina fecha/hora de inicio y autoriza el ingreso.
  - **Si es Rechazado**: Registra el motivo técnico (falta de cobertura, medicamento no domiciliable, etc.).
- **Notificación al Remitente**: Carolina Venencia envía el correo formal de respuesta generado por la IA al remitente con la decisión médica.

### Paso 6: Parametrización en Medifolios y Cuadro de Aplicadores (Atención al Usuario)
- **Responsable**: `franchesca` (Franchesca Triviño).
- **Acción**: Franchesca llama a la familia para confirmar dirección y datos de contacto, crea al paciente en el software institucional **Medifolios** y lo vincula al auxiliar de enfermería (aplicador) asignado a esa zona.

### Paso 7: Protocolo de Alistamiento de Insumos (Inventarios)
- **Responsable**: `german` (German Giraldo).
- **Regla Estricta de Empaque**:
  > [!IMPORTANT]
  > **Tratamientos Menores a 3 Días (< 3 días)**:
  > - 1 Catéter calibre 22
  > - 1 Catéter calibre 24
  > - 2 Tapones venosos
  > - 1 Macrogotero
  > - 1 Jeringa por cada aplicación prescrita
  > - 1 Solución salina 100 cc por cada aplicación
  > - Guantes limpios suficientes por aplicación
  > - Isopañiles / gasas con alcohol
  >
  > **Tratamientos de 3 o Más Días (>= 3 días)**:
  > - La dotación anterior multiplicada proporcionalmente por el número total de días autorizados.

### Paso 8: Censo Diario y Reporte a Entidades (Facturación)
- **Responsable**: `esteban` (Esteban Gacha).
- **Acción**: Esteban registra el ingreso formal en el **Censo Diario**, reportando la novedad a la Secretaría de Salud departamental y a la EPS aseguradora para habilitar la cobertura activa.

### Paso 9: Monitoreo y Módulo de Hospitalización (Atención al Usuario)
- **Responsable**: `yurli` (Yurli).
- **Acción**: Monitorea que cada dosis diaria sea administrada y registrada por el aplicador. Al concluir el ciclo prescrito, genera la salida formal del paciente en el módulo de hospitalización.

### Paso 10: Egreso Médico, Devolución y Facturación Final
- **Dr. Hernando Vence**: Realiza la **visita médica de egreso**, evaluando la resolución del cuadro infeccioso o agudo.
- **German Giraldo**: Recibe y liquida el **reintegro de insumos sobrantes** no utilizados, devolviéndolos al inventario general.
- **Esteban Gacha**: Genera la **facturación electrónica** radicada ante la EPS, y en caso de extensiones autorizadas, liquida el cobro de copagos adicionales.

---

## 5. Centro de Entrenamiento de la Inteligencia Artificial

El sistema cuenta con un motor de IA que puede ser adaptado o re-entrenado en tiempo real sin requerir cambios en el código:

1. Ingrese con el usuario `admin` o cualquier usuario autorizado.
2. Vaya a la pestaña **Configuración**.
3. Desplácese hasta la sección **4. Centro de Entrenamiento de la IA (PADO Agudo & Reglas Asistenciales)**.
4. En este cuadro de texto encontrará las instrucciones en lenguaje natural que la IA lee antes de clasificar cualquier correo.
5. Puede añadir nuevas reglas, por ejemplo:
   - *"Si la EPS es Sanitas, asignar a Esteban Gacha con prioridad Alta."*
   - *"Si el antibiótico es Vancomicina, requerir valoración presencial obligatoria."*
6. Haga clic en **Guardar Configuración**. A partir de ese momento, todos los correos nuevos serán procesados con las nuevas reglas.
7. Si en cualquier momento desea volver a las directrices oficiales de HomeCare del Quindío, haga clic en el botón **Restaurar Instrucciones Oficiales HomeCare**.

---

## 6. Generador y Diseñador de Firma Digital

Para dotar a los correos de salida de validez institucional y médica:

1. En la pestaña **Configuración**, ubique la sección **3. Diseñador de Firma Digital Institucional**.
2. Puede elegir una plantilla rápida:
   - **Clínica / Médica**: Incluye Registro Médico, Coordinación Asistencial y Cláusula de Secreto Profesional.
   - **Corporativa / Administrativa**: Enfocada en Admisiones, Código de Habilitación y PBX.
   - **Sencilla**: Para Atención al Usuario.
3. Al redactar una respuesta o un correo de aceptación, haga clic en el botón **Insertar Firma Digital** para que el texto formateado se incruste automáticamente al final del mensaje.

---

## 7. Instrucciones de Actualización y Despliegue en Servidor

Para sincronizar la última versión en el servidor de producción (`dala@dala-iMac`):

```bash
# 1. Ingresar al directorio del proyecto
cd ~/email-ai-agent

# 2. Descargar los cambios más recientes desde GitHub
git pull origin main

# 3. Reiniciar el servicio en segundo plano
sudo systemctl restart email-ai-agent

# 4. Verificar el estado operativo
sudo systemctl status email-ai-agent
```

> [!TIP]
> **Acceso Remoto Seguro**: El sistema permanece disponible 24/7 en la URL privada de Tailscale Funnel:
> **`https://dala-imac.tail96cdf1.ts.net/correos`**
