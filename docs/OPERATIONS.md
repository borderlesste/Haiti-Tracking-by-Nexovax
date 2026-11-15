# Operación, datos y recuperación

## Arranque local con contenedores

Requisitos: Docker Engine/Desktop con Compose v2. Desde la raíz:

```powershell
Copy-Item .env.example .env
# Cambiar POSTGRES_PASSWORD (solo alfanumérica para este ejemplo), SESSION_SECRET y API_KEY_PEPPER.
docker compose config --quiet
docker compose up --build
```

Web: `http://localhost:4173`. API: `http://localhost:8000/v1/health`. OpenAPI: `http://localhost:8000/docs`. La base nueva y las evidencias usan volúmenes persistentes separados. `docker compose stop` conserva datos. No ejecutar `docker compose down --volumes` salvo que se quiera eliminar conscientemente la base local y las evidencias.

El arranque Compose migra únicamente su base local dedicada. No cargar un `DATABASE_URL` de producción en una sesión de pruebas. El arranque rápido sin contenedores se documenta en el README y no reemplaza las pruebas PostGIS.

La verificación local posterior utilizó un proyecto separado, `haiti-tracking-verify`, con `deploy/verify.compose.yaml`. Sus puertos enlazados a localhost son DB `55433`, API `8002` y web `4174`, distintos de los del arranque normal. La API corre con el usuario no root de su imagen. Mantener el mismo nombre de proyecto y los dos archivos al inspeccionar o detener ese entorno; no confundir sus volúmenes con otra base local:

```text
docker compose -p haiti-tracking-verify -f docker-compose.yml -f deploy/verify.compose.yaml ps
```

No se ha repetido aquí el build ni la suite después de los últimos ajustes de implementación; los resultados de cada ronda se registran por separado en `SECURITY-REVIEW.md`.

## Preparar staging Render + Vercel

1. Elegir una base PostgreSQL/PostGIS **nueva**, separada de RD Marketplace. Confirmar región, TLS, roles y recuperación. No reutilizar una cadena de conexión por similitud de nombre.
2. Crear un respaldo y probar la restauración antes de migrar datos existentes. Revisar la migración y registrar el commit.
3. Configurar `DATABASE_URL`, `WEB_BASE_URL`, `ALLOWED_ORIGINS` (lista exacta), `TRUSTED_HOSTS` (host API y web del proxy), secretos aleatorios distintos, Resend y almacenamiento privado. No poner secretos en `vercel.json`, Git o logs.
4. Revisar el plan y coste de Render: la plantilla propone un servicio `starter`; no ha sido provisionado. Mantener despliegue automático desactivado durante la preparación.
5. Crear en la consola SQL segura un rol LOGIN dedicado, por ejemplo `haiti_api_runtime`, sin superusuario, `BYPASSRLS`, propiedad de tablas ni acceso a otras bases. Su contraseña aleatoria se entrega por gestor de secretos. Ejecutar `python -m app.cli migrate` desde `apps/api` con el rol propietario de migraciones, la base de staging correcta y `BACKEND_DB_ROLE=haiti_api_runtime`: la migración concede las políticas RLS y permisos explícitos del backend; auditoría solo admite SELECT/INSERT. Configurar después `DATABASE_URL` del servicio con el rol runtime, nunca con el propietario. Producción rechaza arrancar con un rol propietario/superusuario/BYPASSRLS. Crear administrador con el comando interactivo `python -m app.cli create-user` y configurar MFA; nunca guardar su contraseña en CI o seed.
6. Reemplazar el origen `.invalid` de `vercel.json` por la URL API HTTPS real. Usar raíz del repositorio en Vercel; el build publica `apps/web/dist/client`. Validar la reescritura con login y cookies desde el dominio web, incluyendo logout, CSRF, origen no autorizado y error API.
7. Probar registro → correo real → verificación → sesión → aporte → revisión por otra cuenta → publicación → lectura API. Probar usuario diferente, residencia privada, token revocado y GPS denegado.
8. Activar producción solo después del piloto y de los controles pendientes en `ACCEPTANCE.md`. No promover una compilación diferente de la probada.

La plantilla no ejecuta migraciones de producción automáticamente. `sync: false` de Render solicita valores al crear el Blueprint; cambios posteriores de variables deben configurarse explícitamente en el servicio. El intento de acceso a Render devolvió `UNAUTHORIZED`: no hubo despliegue remoto. La plantilla no equivale a despliegue ni a comprobación de disponibilidad.

## Respaldos y restauración

Antes de cada migración sensible, registrar destino, versión de esquema, commit, hora UTC y responsable. Confirmar retención y cifrado del proveedor. Respaldar **también** objetos privados y el procedimiento de recuperación de secretos; un dump SQL no contiene archivos.

Ejemplo con herramientas PostgreSQL instaladas y credenciales suministradas por el gestor de secretos mediante `PGSERVICE`/`PGPASSFILE`, nunca como argumento o texto de informe:

```text
pg_dump --service=haiti-staging-backup --format=custom --no-owner --file=haiti-staging.dump
pg_restore --list haiti-staging.dump
pg_restore --service=haiti-isolated-restore --no-owner --no-privileges --single-transaction haiti-staging.dump
```

El destino de restauración debe ser una base temporal vacía. No añadir `--clean` ni restaurar encima de producción durante un ensayo. Los archivos dump deben almacenarse cifrados fuera del repositorio, con permisos restringidos y fecha de expiración.

Validar en la base restaurada: extensiones PostGIS/pg_trgm, versión de migraciones, integridad de FK, recuentos por estado, consulta pública, sesión de prueba, aislamiento y recuperación de una evidencia privada con autorización. Registrar duración observada; no se han certificado RPO/RTO del servicio.

**Ensayo local ejecutado:** `docs/backup-roundtrip.json` registra `passed` con datos exclusivamente sintéticos. Se cifró el dump antes de guardarlo y se restauró en otra base desechable; se verificaron los 721 territorios, un código de ubicación sintética, auditoría y columna espacial. La clave de prueba existió solo en el proceso y no se conservó. El script de ese ensayo usa su propio contenedor de pruebas en `55432`, separado del proyecto Compose en `55433`. No prueba recuperación de objetos S3, sesiones reales, custodia de claves, copias externas programadas, retención ni desastre de producción.

Rollback: detener escrituras, conservar el estado fallido para análisis, restaurar a una base nueva y comprobarla antes de cambiar la conexión del servicio. Revertir código no revierte automáticamente datos. Preferir migraciones compatibles de expansión/contracción y no ejecutar downgrade destructivo con datos de usuarios.

## Catálogo territorial fijado y revisión de nuevas versiones

La implementación incorpora el [recurso COD-AB Haití de HDX](https://data.humdata.org/dataset/cod-ab-hti), con atribución CNIGS/OCHA y licencia CC BY-IGO según `apps/api/data/SOURCE.json`. El archivo original fijado tiene SHA-256 `9601ebe9bf79188d852cce50e846c789b801b10778701fc20355a4e35fd0a67a`; se conserva sin editar en `apps/api/data/hti-cod-ab.geojson.zip`. El importador produce 721 territorios de esta versión y valida checksum, unicidad y jerarquía. La migración conserva los registros ilustrativos anteriores desactivados en vez de eliminarlos.

Los polígonos originales permiten validaciones espaciales con PostGIS. No prueban que todos los nombres o límites sigan vigentes en terreno ni que exista cobertura de establecimientos. La zona piloto y revisión de actualidad requieren validación operativa. El [portal COD de OCHA](https://cod.unocha.org/) y la [guía COD-AB](https://knowledge.base.unocha.org/wiki/spaces/imtoolbox/pages/2557378679) ayudan a revisar nuevas entregas; [UN SALB Haití](https://salb.un.org/en/data/hti) sigue siendo una posible comparación, no otra fuente importada.

Para aprobar un lote: descargar su recurso concreto; conservar URL, editor, fecha, licencia exacta, versión y SHA-256; verificar IDs/pcode, geometrías, nivel administrativo y padres; comparar nombres originales y alias; identificar cambios de límites; revisar compatibilidad de licencia con redistribución API comercial; acordar la zona piloto; importar primero en staging mediante un proceso reproducible y probar que los IDs existentes siguen resolviendo. Guardar un informe de diferencias y aprobación. No codificar un número fijo de comunas o secciones.

## Mapas, archivos y privacidad

Las teselas públicas OpenStreetMap sirven para revisión local conforme a su [política](https://operations.osmfoundation.org/policies/tiles/). No descargar de forma masiva, precargar offline o asumir SLA. Elegir proveedor y presupuesto antes de tráfico comercial; al cambiar host, actualizar la configuración del mapa y la CSP en nginx/Vercel conjuntamente.

Las fotos pendientes son privadas. No habilitar ACL pública de buckets. Verificar autorización de lectura, límites, tipo real de archivo, re-encoding/EXIF y expiración de URLs antes del piloto. La evidencia no se debe publicar directamente por ser subida. Retención de GPS bruta y evidencias requiere una política operativa aprobada; el ejemplo de 30 días del documento no es una regla legal validada.

## Monitorización y respuesta

Monitorizar `/v1/health`, latencia, errores, cuota, intentos fallidos, fallos de correo/almacenamiento y cambios de visibilidad. Usar `request_id` sin almacenar contraseñas, tokens, correos completos o GPS bruto en logs. El comando de uvicorn desactiva access logs para evitar parámetros sensibles en URLs.

Los destinos de alertas y retención de logs deben ser configurados en el proveedor: el repositorio no ha creado alertas remotas. Ante una filtración: limitar temporalmente el recurso afectado, preservar evidencia restringida, identificar alcance, preparar rotación con evaluación de impacto y aprobación del responsable, corregir, probar y documentar. No revocar credenciales ni borrar datos de producción por automatismo.

## Reintentos de correo

Registro, verificación y recuperación crean un trabajo durable con contenido cifrado en la base; el proveedor se invoca después de enviar la respuesta HTTP genérica. Una caída de Resend no debe convertirse en un oráculo de existencia de cuentas. Los fallos registran solo el ID del trabajo y conservan el envío para reintento con una clave de idempotencia estable.

Programar `python -m app.cli deliver-mail` desde `apps/api` cada cinco minutos en el entorno del backend, con el mismo cifrado, base de datos y credencial de correo. La plantilla no crea ese cron remoto. El comando procesa trabajos vencidos con lease, backoff y máximo de intentos; monitorizar trabajos pendientes y agotados sin revelar su contenido. La cola permite recuperar envíos tras un reinicio, pero no garantiza entrega sin un ejecutor de reintentos operativo. Al rotar `SESSION_SECRET`, considerar los trabajos cifrados y MFA existentes: no cambiarlo sin plan de recifrado y recuperación.

## Validación de infraestructura disponible

- `render.yaml`: validado localmente contra el JSON Schema oficial de Render el 2026-11-14; sin aplicación remota.
- Docker/Compose: verificación local ejecutada en `haiti-tracking-verify`, DB `55433`, API `8002`, web `4174`; API sin root. Recompilado y arrancado tras los cambios finales de API y web; sin despliegue remoto.
- PostgreSQL/PostGIS: cuatro casos de integración cubren consulta en metros/índice espacial, auditoría append-only, rol runtime con RLS y publicación concurrente. La última ronda completa local terminó con 36 pruebas aprobadas, incluidas cuatro de PostGIS.
- Backup: ensayo sintético cifrado/restaurado registrado en `docs/backup-roundtrip.json`; recuperación del entorno real pendiente.
- Catálogo: lote HDX/CNIGS/OCHA de 721 territorios fijado por checksum, con procedencia y licencia en `SOURCE.json`.
- Render remoto: `UNAUTHORIZED`; ningún servicio desplegado.
- Vercel: JSON preparado con origen deliberadamente no resoluble; falta vinculación, origen HTTPS y despliegue de staging.
- Supabase: ninguna migración, permiso, secreto, bucket o servicio remoto fue modificado.
- GitHub Actions: workflow preparado, con barrido de secretos, SAST y auditorías de dependencias. Repositorio privado creado; primer push con `[skip ci]` hasta confirmar cuota incluida/bloqueo de gasto. No hay run remoto certificado.

## Retención GPS y migración de relaciones

`python -m app.cli purge-gps --retention-days 30` simula y solo informa cuántos registros cumplen el plazo. `--apply` exige una ejecución explícita de la política aprobada: elimina la lectura del dispositivo y su distancia, conserva el punto canónico propuesto, incrementa la versión y registra la acción sin coordenadas. Los aportes pendientes pasan a revisión adicional y requieren corroboración independiente antes de aprobar. No se ha creado una tarea automática ni aplicado una purga a los datos de uso normal. Treinta días es un valor inicial propuesto, pendiente de revisión legal/operativa; la retención de backups, fotos y auditoría debe definirse por separado. Un backup cifrado antiguo puede conservar datos anteriores hasta que venza su política.

La migración `0003_location_relationships` agrega alias y relaciones sin borrar registros, verifica FK/autorreferencias/ciclos e incorpora índices. PostgreSQL serializa las mutaciones canónicas de la API. El ensayo previo de backup y restauración local se registra en `schema-backup-check.json`. El downgrade de 0003 conserva estas columnas para evitar pérdida de datos; una reversión física exige un plan de restauración revisado. El downgrade total se prueba únicamente en bases desechables y está bloqueado en producción.
