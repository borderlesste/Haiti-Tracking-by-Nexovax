# Trazabilidad del maestro y pendientes

Fuente: `HaitiTrackingbyNexovax.md`, conservado sin modificar. La referencia visual es orientativa según §6.6. Este registro distingue código implementado, evidencia local y validación operativa; no declara listo el piloto completo.

| Maestro | Implementación | Evidencia y límite |
| --- | --- | --- |
| §1–4, §23.1: MVP y roles | Lugares públicos, usuario/moderador/admin, perfiles de uso, permisos en servidor; dinero y residencias deshabilitados | Tests de roles, mass assignment, autoaprobación y privacidad. No se intervino RD Marketplace |
| §5 HU01, §6.2 inicio/mapa | Home, Leaflet, búsqueda anónima, filtros, resultados y CTA | Navegador móvil/desktop; ninguna solicitud GPS al consultar. Datos demo solo en QA y marcados |
| §5 HU02, §3.2 | Registro, verificación, login/logout, recuperación, sesiones y MFA de staff | API y navegación con correo local. Entrega externa Resend pendiente |
| §6.2 ficha pública | Dirección, código, acceso, referencias, confianza, fecha, compartir/QR, reporte y corrección | QR decodificado independientemente; diálogo/copiar/Escape/foco verificados |
| §6.3 datos territoriales | Departamento/comuna, sección opcional, barrio/referencia; calle/número opcionales | Catálogo real versionado y borrador reabierto con sección; errores/reintento de carga |
| §6.3 coordenadas, §8 | GPS por botón, timestamp/precisión/fuente, lectura original separada del pin y círculo; explicación al mover más de 50 m | Tests de límites/frescura/distancia, errores de permiso/timeout; calibración y GPS físico pendientes |
| §6.3 evidencia | Fuente de conocimiento, descripción, fotos opcionales privadas y declaración de derechos | Límites tipo/tamaño, re-encode/EXIF, IDOR y recuperación parcial de carga comprobados |
| §6.3 revisión final | Coincidencias, enlaces Es este lugar/Proponer corrección, justificación de lugar distinto y resumen antes de enviar | Validación API y UI implementadas. Resumen y confirmación pasan en Chromium con respuesta GPS ficticia; GPS físico pendiente |
| §6.3 recibo, §6.4 estados | ID, fecha, estado, motivo, corrección, retiro por autor antes de decisión | UI y tests de versión/propiedad/rechazo de aprobación tras retiro |
| §6.5 idioma y accesibilidad | ES/FR/HT, etiquetas/foco/errores, coordenadas editables por teclado y modales compartidos | Navegación y responsive verificados; revisión nativa, lector de pantalla y auditoría WCAG completa pendientes |
| §7.1, §17 catálogo | 721 territorios fijados con jerarquía, alias, fuente/licencia/SHA; importación idempotente; edición versionada por admin | Migraciones, catálogo y QA. Actualidad de límites y selección piloto requieren revisión local |
| §7.2 relaciones/unidades | FK parent/access, unidad e indicaciones, códigos públicos de relación, alias originales/normalizados | Ciclos/autorreferencias/tipo de entrada/privacidad y fusiones con referencias/versiones probados |
| §7.3 códigos, §12.6 | Contador transaccional HT-NXV, códigos estables y redirecciones de fusión | Concurrencia y conservación de referencias en PostgreSQL |
| §7.4, §10 calidad | Confianza explicada como indicador, fecha y estado; 150 m requiere revisión/corroboración adicional | Tests de incertidumbre y evidencia independiente. No prueba criptográfica de presencia |
| §8.2 retención | CLI dry-run por defecto; aplicar elimina lectura/distancia, conserva propuesta, versiona/audita y exige corroboración | Prueba dry-run/aplicación/idempotencia. Plazo inicial 30 días propuesto; política legal, backups/fotos y cron pendientes |
| §9 duplicados | Radio PostGIS, nombres/alias, distancia/similitud/categoría, justificación y recheck bajo lock al publicar | Casos cercanos, dos negocios legítimos, carrera y merge. Umbrales pendientes de calibración del piloto |
| §10 moderación | Bandeja segura, GPS/pin/evidencia/candidatos, aprobar/rechazar/cambios/fusión, motivo e historial | Tests de roles/transiciones/MFA/auditoría. Cada publicación exige decisión humana |
| §10.4 reportes | Reporte público limitado, prioridad de privacidad y ocultación administrativa | Navegador y API: ficha oculta devuelve 404 y desaparece del buscador |
| §11 pagos | Recompensas monetarias, cobros y payouts inactivos | Stripe/PayPal sin operaciones; sus controles financieros pertenecen a fase posterior |
| §12 búsqueda/código/nearby | DTO público explícito, paginación/cursor firmado y distancias en metros | Tests privacidad, límites, error normalizado, geografía e índices |
| §12.8 geocode/reverse | Candidatos textuales con filtro de comuna; reverse calcula zona con polígonos PostGIS y lugares públicos | Prueba de comuna, zona, punto exterior y privacidad. SQLite local declara sin límites espaciales; indexar límites según carga medida |
| §12.3 claves, §16 portal | Apps test/live, secreto una vez/hash, caducidad, reautenticación, revocación, cuota y consumo | Pruebas 401/403/429, IDOR, propietario activo y concurrencia de consumo |
| §12.4–12.11 contrato | Pydantic, OpenAPI, request ID, estados/error uniformes, entradas y métodos rechazados | `apps/api/openapi.json` generado del código. Validación del consumidor remoto pendiente |
| §13 modelo propuesto | SQLAlchemy/PostGIS, restricciones, índices, versiones/reviews, RLS backend; alias y GPS en JSON validado | Mismo dominio sin tablas redundantes. Los límites se leen del archivo fijado; no se afirma un GiST territorial existente |
| §14 entornos/infra | Dev, tests y producción estricta; Docker sin root en API, bases fijadas, Render/Vercel/Supabase preparados | Compose local y pruebas reales PG. Staging gratuito bloqueado por conexión/cupos; ninguna plantilla equivale a despliegue |
| §15 seguridad | Argon2id, cookies, CSRF/origen, MFA, RBAC/IDOR, no-store, CSP, cuerpos, archivos y logs sin entradas privadas | Informe obligatorio de seis partes en `SECURITY-REVIEW.md`, auditorías y regresiones. Riesgos OS residuales explícitos |
| §18 operación | Backups cifrados/restaurados locales, cola de mail con reintento, auditoría append-only y guía de recuperación | Custodia off-site, alertas, tareas programadas y RPO/RTO operativos pendientes |
| §18 desempeño, §19 pruebas | Suites API/PostGIS/web/Sites, análisis de dependencias/SAST/secretos/imágenes y QA de navegador/red lenta | P95, carga distribuida, dispositivos reales y proveedores reales y CI remoto no certificados |
| §20 DoD | Matriz detallada en `ACCEPTANCE.md` | Siguen abiertos CI remoto, servicios reales, GPS físico, correo/almacenamiento reales, revisión editorial/legal/operativa y piloto territorial |

No se construyen como pagos activos funciones que el maestro excluye del MVP: reputación de fase 2, PWA offline, residencias compartidas, campañas monetarias o facturación comercial. El despliegue respeta la autorización de usar únicamente recursos gratuitos; los requisitos abiertos se conservan como pendientes y no se sustituyen por versiones efímeras sin persistencia.
