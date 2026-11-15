# Arquitectura y decisiones

Fecha de revisión: 2026-11-14. Fuente de requisitos: `HaitiTrackingbyNexovax.md` v1.0. Este archivo describe la implementación en revisión y sus límites; no certifica un servicio de producción.

## ADR-0001 — Web React con API FastAPI independiente

La aplicación parte de cero; la carpeta contenía el documento y la referencia visual. Se adopta React + Vite para la web y FastAPI para toda operación sensible. El documento propone Next.js como recomendación revisable: la separación permite una entrega estática ligera y una API Python única. No hay un segundo backend de negocio en el navegador. El coste de esta decisión es que las fichas públicas de la SPA no tienen prerenderizado por ubicación; SEO avanzado queda pendiente.

| Responsabilidad | Propietario |
| --- | --- |
| Pantallas, traducciones, mapa, permiso GPS | `apps/web` |
| Sesiones, RBAC, privacidad, publicación, cuotas, claves | `apps/api` |
| Fuente de verdad del piloto | PostgreSQL + PostGIS |
| Base del arranque rápido local | SQLite; nunca certifica rendimiento o concurrencia PostgreSQL |
| Correo transaccional | Resend cuando se configure un remitente verificado; outbox solo en desarrollo |
| Evidencias | Almacenamiento privado S3 compatible en producción; directorio local solo en desarrollo |
| Teselas de demostración | OpenStreetMap, con atribución; proveedor comercial y presupuesto pendientes |

## ADR-0002 — Un solo origen web

El navegador solicita rutas relativas `/v1`. En desarrollo Vite hace proxy a `127.0.0.1:8000`. Docker sirve la web con nginx y hace proxy a `api:8000`. Vercel requiere reemplazar `https://api.example.invalid` en `vercel.json` por el origen HTTPS real antes de publicar. El dominio `.invalid` hace fallar una configuración incompleta sin enviar datos a un tercero.

Las cookies de sesión pertenecen al origen web. Las operaciones mutables comprueban CSRF y origen en el servidor; el proxy no reemplaza esa autorización. No se inyectan credenciales de Resend, base de datos, S3, Stripe, PayPal o Supabase en variables públicas `VITE_*`. El CDN no debe cachear `/v1`; la plantilla de Vercel desactiva expresamente la caché de reescrituras externas.

## ADR-0003 — Base nueva aislada; migraciones explícitas

Este proyecto no es RD Marketplace. No se presupone ninguna relación con sus 302 tablas ni autorización para modificarlas. La base de este producto debe ser nueva y aislada. Las migraciones se ejecutan desde `apps/api` con `python -m app.cli migrate`, después de comprobar destino y respaldo. `DATABASE_AUTO_CREATE=false` en Render evita cambios automáticos al arrancar.

Supabase es una opción de alojamiento PostgreSQL/PostGIS, no un segundo sistema de autenticación. La API debe usar un rol de ejecución dedicado, sin permisos administrativos ni `BYPASSRLS`. El rol de migraciones y el rol de ejecución deben ser distintos antes de producción. Las tablas de sesiones, GPS, auditoría y claves no se exponen a `anon`/`authenticated` mediante Data API. Revisar RLS y privilegios reales en el proyecto elegido: esta entrega no ha alterado ningún proyecto Supabase remoto.

## ADR-0004 — Piloto sin dinero real ni viviendas públicas

Recompensas monetarias, cobros y payouts permanecen deshabilitados. Las etiquetas Stripe y PayPal del encargo no sustituyen las decisiones comerciales pendientes del documento. No se crean productos, suscripciones, transferencias o cargos en proveedores. Tampoco se publican residencias privadas ni se implementan enlaces privados sin un procedimiento de titularidad aprobado.

La evidencia de GPS es una observación del navegador, no una prueba criptográfica de presencia. El servidor conserva su precisión y exige moderación; no permite al cliente asignar estado verificado, confianza, importe o código canónico.

## ADR-0005 — Catálogo territorial CNIGS/OCHA versionado

El catálogo inicial ilustrativo fue sustituido por el recurso COD-AB Haití de CNIGS/OCHA publicado en HDX. El archivo original `apps/api/data/hti-cod-ab.geojson.zip` se conserva junto a `SOURCE.json`, que registra recurso, SHA-256, fecha, atribución y licencia CC BY-IGO. El importador verifica el checksum, los identificadores y sus padres antes de cargar 721 registros de esta versión: país, departamentos, comunas y secciones comunales. Estos recuentos describen el lote fijado, no una regla administrativa permanente.

Los GeoJSON incluyen polígonos; PostGIS permite comprobar discrepancias entre un punto y el territorio declarado. Una coincidencia espacial no certifica la presencia física ni la identidad de un establecimiento. La selección de la zona piloto, validación local de actualidad y gobierno de futuras revisiones siguen pendientes. Ver `OPERATIONS.md`; no sustituir IDs existentes por una lista manual ni interpretar el catálogo como cobertura de POI verificados.

## Despliegues previstos

- Local rápido: Python + SQLite y Vite, útil para revisar UI y flujos funcionales.
- Local reproducible: Docker Compose con PostgreSQL/PostGIS, API y nginx; todos los puertos enlazados a `127.0.0.1`.
- Verificación local aislada: proyecto Compose `haiti-tracking-verify`, con override `deploy/verify.compose.yaml`: base en `55433`, API en `8002` y web en `4174`. La API utiliza el usuario no root definido en su Dockerfile.
- Staging: API Render y PostgreSQL/PostGIS dedicado (por ejemplo Supabase), web Vercel mediante proxy HTTPS.
- Producción: pendientes proveedor cartográfico, remitente de correo, almacenamiento privado, permisos del destino real, carga, custodia de respaldos y piloto humano. Existe un ensayo local de backup sintético cifrado/restaurado (`docs/backup-roundtrip.json`); no certifica recuperación del servicio de producción.

No se ha desplegado infraestructura remota. El acceso de Render devolvió `UNAUTHORIZED`; su Blueprint sigue siendo una plantilla sin aplicar. La verificación Docker local y los cuatro casos PostGIS no sustituyen el despliegue ni las pruebas del proveedor elegido. La última ronda local sobre el estado final pasó 36 pruebas, incluidas las cuatro de PostGIS; no certifica el entorno remoto.

## Referencias verificadas

Consultadas el 2026-11-14:

- [Render Blueprint YAML](https://render.com/docs/blueprint-spec.md).
- [Variables de entorno Render](https://render.com/docs/configure-environment-variables.md).
- [Rewrites Vercel y caché de orígenes externos](https://vercel.com/docs/routing/rewrites).
- [Supabase PostGIS](https://supabase.com/docs/guides/database/extensions/postgis).
- [Supabase changelog](https://supabase.com/changelog.md); los cambios recientes de CLI no afectan a esta API SQLAlchemy sin CLI Supabase.

## Relaciones, nombres y observaciones

Las ubicaciones mantienen alias originales y texto de búsqueda normalizado; entradas y edificios se relacionan por FK privadas, y el DTO resuelve únicamente códigos públicos de registros activos. Una relación oculta se devuelve nula. Se rechazan autorreferencias, ciclos de edificio y entradas de tipo incorrecto, también al aprobar. Las fusiones conservan códigos, nombres alternativos y versiones, redirigen referencias entrantes y rechazan destinos descendientes o una pérdida de semántica de acceso. La API bloquea fusiones con más de diez alias para exigir revisión en vez de descartarlos.

El modelo de tablas de la sección 13 del maestro es propuesto. Aquí los alias son un array JSON validado y la observación GPS vive en el payload privado de la contribución; no se duplican tablas para la misma responsabilidad. Los límites territoriales se leen del archivo GeoJSON versionado y se verifican con ST_Covers en PostgreSQL. No se afirma disponer de una columna boundary/GiST territorial: el GiST actual corresponde al punto de las ubicaciones. Evaluar materializar límites si el perfil real del piloto justifica esa migración.

Reverse recorre de país a sección los límites versionados con ST_Covers en PostgreSQL; SQLite local declara explícitamente que no ofrece esta resolución. El filtro commune_id de geocode incluye sus secciones. Este recorrido es suficiente para comprobación local; materializar e indexar polígonos exige medir carga antes de ampliar el piloto.
