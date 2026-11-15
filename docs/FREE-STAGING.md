# Staging con recursos gratuitos

Revisión: 2026-11-15. Restricción del propietario: **solo recursos gratuitos**, sin crear cargos ni contratar planes pagados. Se preparó `deploy/render-free.yaml`; no se aplicó a Render ni se modificó `render.yaml` principal, que conserva su propuesta `starter` y **no debe utilizarse para este despliegue gratuito**.

La variante mantiene la aplicación y sus flujos: registro/verificación/recuperación, sesiones/MFA, GPS, propuestas, evidencias, moderación, API y claves. No sustituye PostgreSQL por SQLite efímero, no elimina el correo o las fotos, ni habilita dinero real. Preparar una plantilla no garantiza coste total cero: falta confirmar elegibilidad, cupos y condiciones de todos los servicios antes de provisionar.

## Estado y bloqueos comprobados

| Componente | Estado y condición |
| --- | --- |
| Render | El conector devolvió `UNAUTHORIZED`; no hay servicio creado ni despliegue remoto. La variante fija `plan: free` y despliegue por commits desactivado. |
| Base de datos | Falta una base PostgreSQL/PostGIS nueva y aislada, con asignación gratuita legítima, persistencia, TLS y roles separados. Ninguna URL o clave existente se reutiliza. |
| Supabase | El inventario comunicado por el responsable muestra NexovaxLLC en `tier_free` con dos proyectos `ACTIVE_HEALTHY`, ninguno de Haiti Tracking. La cuota gratuita está ocupada; no se pausa, borra ni migra otro proyecto para liberar sitio. |
| Correo y archivos | Se requieren Resend real con remitente verificado y almacenamiento S3 privado persistente. No se ha demostrado que exista cupo gratuito utilizable para ambos en una cuenta autorizada. |
| Web | Se requiere hosting HTTPS con proxy `/v1` del mismo origen. El conector Vercel no expuso el plan de facturación; no se presume elegibilidad gratuita. |

Supabase permite dos proyectos gratuitos activos en conjunto entre las organizaciones donde la persona es Owner o Administrator; crear otra organización con el mismo titular no evita ese límite. La disponibilidad debe resolverse sin tocar recursos de otros productos y sin contratar un plan. [Facturación oficial de Supabase](https://supabase.com/docs/guides/platform/billing-on-supabase).

Vercel Hobby está destinado a uso personal no comercial. Un staging de un producto empresarial no se vuelve elegible solo por no cobrar todavía. Mientras no se confirme elegibilidad o una alternativa gratuita compatible, la web remota queda pendiente. [Planes de Vercel](https://vercel.com/pricing), [Hobby](https://vercel.com/docs/plans/hobby).

## Alcance de la variante Render

El Blueprint declara **una API free**, sin base Render, disco, worker, cron ni escalado pagado. El plan web `free` figura con 0.1 CPU y 512 MB; esta capacidad requiere medir la carga real de Argon2, imágenes y concurrencia. [Compute plans](https://render.com/docs/compute-plans).

Render Free se duerme tras 15 minutos inactivo, tarda aproximadamente un minuto en despertar y pierde archivos locales al reiniciar. No admite discos persistentes, shell/SSH ni one-off jobs. Sus 750 horas mensuales se comparten por workspace. Builds y transferencia tienen cuotas; con método de pago, ciertos excesos pueden generar cargos. Por ello no se promete gasto cero ni se aplica la plantilla hasta revisar límites y facturación. [Limitaciones oficiales](https://render.com/docs/free).

No se incluye Render Free Postgres como persistencia del producto: expira a los 30 días y no dispone de backups gestionados. No ofrece la continuidad requerida para conservar cuentas, propuestas y auditoría de este staging. [Free Postgres](https://render.com/docs/free#free-postgres).

`autoDeployTrigger: off` evita nuevos despliegues por commits; **no impide el primer despliegue si se aplica el Blueprint**. La creación/aplicación inicial también debe ser una acción manual, después de resolver los bloqueos. No hay `preDeployCommand`, hook de seed ni migración automática. [Referencia Blueprint](https://render.com/docs/blueprint-spec).

## Configuración que conserva seguridad y persistencia

| Variable / requisito | Valor o propósito |
| --- | --- |
| `APP_ENV=production` | Es el perfil de seguridad que ya entiende la aplicación: HTTPS, cookies Secure, rol DB restringido y proveedores reales. El código solo admite development/test/production; se conserva este perfil en **staging**, sin promoverlo a producción comercial. Usar development/test debilitaría controles. |
| `DATABASE_AUTO_CREATE=false` | El arranque del servicio no crea ni migra el esquema. |
| `DATABASE_URL` | Secreto `sync: false` de una base externa nueva PostgreSQL/PostGIS, TLS y rol runtime no propietario. Debe seguir siendo duradera si la API se duerme. |
| `BACKEND_DB_ROLE` | Rol `haiti_api_runtime`, sin superusuario/BYPASSRLS/propiedad, con las políticas explícitas preparadas mediante migración controlada. |
| `WEB_BASE_URL`, `ALLOWED_ORIGINS`, `TRUSTED_HOSTS`, `FORWARDED_ALLOW_IPS` | URL HTTPS de staging, orígenes/hosts exactos y proxies legítimos. No copiar dominios productivos ni aceptar proxies arbitrarios. |
| `SESSION_SECRET`, `API_KEY_PEPPER` | Secretos distintos generados al crear el servicio. Guardar su recuperación fuera del filesystem efímero; una rotación requiere considerar MFA y trabajos cifrados. |
| `RESEND_API_KEY`, `EMAIL_FROM` | Credencial y remitente reales, con elegibilidad y cuota gratuitas verificadas; no se usa outbox local. |
| `S3_*` | Bucket privado S3 compatible, persistente y autorizado, con cifrado y cuota gratuita comprobada; no se guardan evidencias en el disco efímero. |
| `REWARDS_CASH_ENABLED=false` | Sin cobros, recompensas monetarias o payouts. |

Resend anuncia actualmente 3.000 correos/mes y 100/día en Free. Verificar el plan efectivo y el remitente antes de usarlo; no activar pay-as-you-go ni ampliar planes para superar esa cuota. [Cuotas de Resend](https://resend.com/pricing).

La ausencia de almacenamiento privado o correo real es un requisito pendiente, no una autorización para ocultar esos flujos o cambiar su comportamiento. Los límites gratuitos pueden retrasar/suspender el servicio; no deben convertirse en publicación automática, pérdida de datos o promesas de entrega de correo.

## Secuencia prevista cuando existan recursos elegibles

1. Confirmar con el propietario el destino nuevo, cuentas autorizadas y cupos gratuitos, sin habilitar extras facturables. Conservar intactos los proyectos ajenos. Si no existe capacidad gratuita que mantenga el alcance, dejar el despliegue pendiente.
2. En una base de staging nueva, preparar roles y respaldo/restauración. Ejecutar las migraciones revisadas desde un equipo autorizado con conexión TLS y rol de migraciones; después usar solo el rol runtime en Render. Free no proporciona shell/one-off jobs para esta tarea. No migrar durante el arranque ni contra otra aplicación.
3. Preparar remitente Resend y bucket privado reales con acceso mínimo. Comprobar cuotas, retención y recuperación. Resolver el hosting web gratuito con proxy del mismo origen y elegibilidad de uso.
4. Revisar `deploy/render-free.yaml` y la colección completa de secretos, confirmar manualmente el plan Free y aplicar únicamente ese servicio de staging. Esta documentación no ha realizado ese paso.
5. Probar desde la web HTTPS: registro → correo → verificación → sesión → GPS → propuesta → evidencia privada → revisión por otra cuenta → publicación → API; probar errores, denegación GPS, IDOR, clave revocada, límites y persistencia tras reinicio/cold start. No declarar el entorno listo con un health check aislado.
6. Ejecutar `python -m app.cli deliver-mail` desde un ejecutor autorizado que ya exista o tenga un cupo gratuito confirmado. La cola cifrada vive en PostgreSQL y permite reintentos; Render Free no incluye un worker/cron en esta variante. Mantener recuperación manual documentada hasta disponer de un ejecutor fiable, sin borrar trabajos ni desactivar registro/recuperación.

## Validación y límites del trabajo realizado

Validación local ejecutada el 2026-11-15: **PASS** contra el JSON Schema oficial de Render y las invariantes de plan free, secretos externos, ausencia de disco/DB/cron y despliegue/migración no automáticos. La comparación semántica con el Blueprint principal confirma solo dos diferencias: nombre del servicio y plan `starter` → `free`; no se modifican comandos ni flujos. Esta validación no crea recursos, verifica facturación de cuentas ni prueba los proveedores remotos. El estado `UNAUTHORIZED`, la cuota Supabase ocupada y los proveedores pendientes siguen bloqueando una entrega remota completa dentro de la restricción gratuita.

No se modificaron servicios existentes, no se habilitó producción y no se autorizó gasto. La plantilla principal y el resto del código permanecen intactos.

## GitHub Actions y presupuesto cero

Repositorio privado creado: `borderlesste/Haiti-Tracking-by-Nexovax`. Las credenciales disponibles no permiten consultar la cuota/facturación de Actions (endpoint antiguo retirado y uso actual no accesible). El primer push se hace con `[skip ci]` para no lanzar cómputo potencialmente facturable. El workflow conserva pruebas automáticas para pushes/PR y ejecución manual, con límite de diez minutos por job. Antes de lanzarlo en GitHub, el propietario debe confirmar minutos incluidos disponibles o bloqueo de gasto. Las suites locales API, web y navegador, build y análisis sí se ejecutaron; sus resultados actuales constan en `verification-final.json`; no se presentan como un run remoto verde.
