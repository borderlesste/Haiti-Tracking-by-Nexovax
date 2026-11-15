# Haiti Tracking by Nexovax

Repositorio privado: https://github.com/borderlesste/Haiti-Tracking-by-Nexovax

Plataforma colaborativa de lugares públicos de Haití: mapa, búsqueda, propuestas con GPS explícito, borradores, moderación humana y API con claves revocables. Incluye QR, alias locales, relaciones entre edificios/entradas, retiro de propuestas y retención GPS explícita. Implementada a partir de `HaitiTrackingbyNexovax.md` y la referencia visual suministrada. El documento maestro y la imagen original se conservan sin cambios.

**Estado: versión local verificable; certificación del piloto y despliegue remoto pendientes.** No hay pagos, recompensas monetarias activas, domicilios privados publicados ni contadores de cobertura inventados. Los lugares de demostración solo se insertan mediante un comando explícito y quedan identificados.

## Inicio local en Windows

Requiere Node.js 22 o superior, pnpm 11.25 y Python 3.12. En PowerShell, desde este directorio:

```powershell
python -m venv apps/api/.venv
apps/api/.venv/Scripts/python.exe -m pip install -r apps/api/requirements.txt
pnpm.cmd --dir apps/web install --frozen-lockfile
node scripts/dev.mjs
```

Abrir **http://127.0.0.1:3000/**. El lanzador inicia también la API en `127.0.0.1:8000`, aplica el esquema de desarrollo e importa el catálogo territorial fijado. SQLite es el modo de desarrollo; PostGIS es el destino de producción. No se necesita una credencial externa para revisar la aplicación local.

Usar la dirección IPv4 exacta: `localhost` puede resolver a otro proceso IPv6 de este equipo. Si los puertos están ocupados, el lanzador se detiene sin cerrar procesos existentes:

```powershell
$env:DEV_PORT='3005'
$env:API_PORT='8005'
node scripts/dev.mjs
```

Opcionalmente copiar `.env.example` a `.env`. Contiene marcadores de desarrollo, nunca credenciales de producción. El lanzador carga ese archivo; los comandos Python directos usan variables del proceso. No imprimir ni subir `.env`, `.runtime` o la bandeja de correo local.

En Linux/macOS, crear el mismo entorno virtual y usar `apps/api/.venv/bin/python` en lugar de `Scripts/python.exe`.

## Recorrido de revisión

- `/`: portada, estadísticas de la base actual y mapa real. `/mapa`: búsqueda anónima sin GPS ni cuenta; sugerencias sin publicación automática.
- `/registro`, `/verificar`, `/acceso`, `/recuperar`, `/restablecer`: cuentas, enlaces de un solo uso y sesiones. Sin Resend configurado en desarrollo, el correo queda en `apps/api/.runtime/outbox`.
- `/contribuir/nueva`, `/contribuciones`: propuestas, dirección sin calle/número, pin, precisión GPS, duplicados, fotos privadas y edición de borradores. La denegación GPS permite guardar un borrador; nunca genera verificación presencial.
- `/cuenta`: perfil, sesiones, exportación y solicitud de eliminación revisable.
- `/desarrolladores`, `/desarrolladores/documentacion`, `/desarrolladores/panel`: documentación, aplicaciones, claves mostradas una vez, cuotas, consumo y revocación con reautenticación.
- `/admin`: revisión con motivos, aprobación/rechazo/cambios/fusión, reportes, sugerencias y catálogo. Auditoría solo para administradores. Todos los permisos se comprueban en el servidor; el rol no se elige en el registro.

Para crear un operador local, ejecutar desde `apps/api`:

```powershell
.venv/Scripts/python.exe -m app.cli create-user
```

El comando solicita contraseña de manera oculta y, para personal autorizado, secreto y código del autenticador. No existe una contraseña administrativa predeterminada. Las cuentas del fixture de navegador se limitan a una base de QA separada y no se cargan durante el inicio normal.

La interfaz incluye español, francés y kreyòl. La revisión editorial por hablantes nativos sigue siendo requisito del piloto.

## PostgreSQL/PostGIS con Docker

`docker-compose.yml` incluye base aislada, API y web. Antes de arrancar, configurar un `.env` local con contraseñas y secretos aleatorios distintos; los marcadores del ejemplo no sirven para producción.

```powershell
docker compose up --build -d
```

Web: `http://127.0.0.1:4173/`. La API usa un usuario de sistema sin root. Las migraciones Alembic importan el catálogo de 721 registros con jerarquía, fuente y licencia. El archivo fijado se verifica por SHA-256; no equivale a un inventario de lugares verificados ni garantiza actualidad de límites administrativos.

Durante esta entrega se comprobó otro proyecto Compose, `haiti-tracking-verify`, con `deploy/verify.compose.yaml`: web `4174`, API `8002`, PostgreSQL `55433`. Sus volúmenes están separados. La configuración normal no se conectó a bases de producción.

## Pruebas

```powershell
pnpm.cmd --dir apps/web test
pnpm.cmd --dir apps/web run test:sites
pnpm.cmd --dir apps/web run build
pnpm.cmd --dir apps/web audit
Set-Location apps/api
.venv/Scripts/python.exe -m pip install -r requirements-test.txt
.venv/Scripts/python.exe -m pytest -q
```

Para incluir las seis pruebas PostgreSQL, establecer `TEST_DATABASE_URL` hacia una **base desechable cuyo nombre contenga `test`**, con PostGIS/pg_trgm disponibles. Las pruebas crean y eliminan únicamente esquemas y roles temporales de esa base. Nunca usar una URL de producción. Sin esa variable los seis casos PostGIS se omiten; el informe debe indicarlo.

Última ronda local: **54 pruebas Python aprobadas en Windows y Linux, incluidas seis PostGIS; 10 pruebas web/Sites aprobadas**. Dos advertencias: deprecación de Starlette/httpx y reflexión del tipo geography. El build pasa y avisa de un bundle inicial de aproximadamente 568 KB minificados (168 KB gzip estimados por Vite). La medición de red lenta anterior y la transferencia del build actual se distinguen en `docs/transfer-check.json`; el rendimiento real sigue pendiente de piloto. Evidencia: `docs/BROWSER-QA.md`, `docs/SECURITY-REVIEW.md`, `design-qa.md`.

## Despliegue y operación

Las plantillas `render.yaml`, `vercel.json` y `.github/workflows/ci.yml` están preparadas. El primer push omite CI hasta confirmar cuota gratuita de Actions; no hay un run remoto certificado. **No ejecutar una publicación usando los marcadores `.invalid`.** Ver `docs/OPERATIONS.md` para rol de migración frente a runtime, TLS/proxy de confianza, PostGIS, correo, almacenamiento privado, backup y restauración.

El propietario autorizó únicamente recursos gratuitos. El destino propuesto es un entorno de staging nuevo y aislado: API en Render, frontend en Vercel y PostgreSQL/PostGIS dedicado en Supabase o servicio compatible. Render requiere reconexión de la cuenta. La creación de recursos de pago, credenciales y cambios en servicios de producción exige revisar impacto y autorización del propietario. Ningún proyecto Supabase existente fue modificado. La organización gratuita tiene sus dos cupos activos ocupados; ver `docs/FREE-STAGING.md` y la variante `deploy/render-free.yaml`. No se contrató ningún plan de pago.

Resend tiene adaptador con cola cifrada y reintentos; falta la prueba de entrega externa. Stripe/PayPal quedan sin operaciones financieras por las exclusiones expresas del MVP. LottieFiles proporciona la animación de GPS; no sustituye la captura real.

## Documentación

- `docs/ARCHITECTURE.md`: dominios, API y límites de confianza.
- `docs/SECURITY-REVIEW.md`: hallazgos, cambios, pruebas y riesgos residuales.
- `docs/ACCEPTANCE.md`: los 24 criterios del maestro y condiciones aún pendientes.
- `docs/OPERATIONS.md`: configuración, migraciones y recuperación.
- `docs/BROWSER-QA.md`: recorrido real del navegador, errores y estados verificados.
- `DESIGN.md`, `UX-CONTRACT.md`, `design-qa.md`: sistema visual, interacción y comparación con referencia.
- `apps/api/openapi.json`: contrato generado; servido también por `/openapi.json`.
- `apps/api/data/SOURCE.json`, `apps/web/public/assets/SOURCES.md`: procedencia y licencias.

No se declara una auditoría de RD Marketplace ni de sus 302 tablas: ese sistema no forma parte del código ni de la base dedicada de Haiti Tracking.

La ronda final local del 2026-11-15 confirmó 54 pruebas API (cinco PostGIS), 10 pruebas web/Sites y build. Ver `docs/SECURITY-REVIEW.md`, `docs/ACCEPTANCE.md` y `docs/REQUIREMENTS-TRACE.md` para evidencias y pendientes. Las imágenes conservan avisos OS residuales: no se declara certificación de producción.
