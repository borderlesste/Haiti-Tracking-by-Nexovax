# Criterios de aceptación y límites del piloto

Referencia: sección 20 del documento maestro. Este registro separa implementación local de certificación operativa. Un archivo de configuración o una pantalla no demuestra que un servicio externo funciona.

| # | Criterio | Evidencia / validación exigida |
| --- | --- | --- |
| 1 | Inicio reproducible, sin secretos | README, `.env.example`, dependencias y CI; comprobar arranque limpio |
| 2 | PostgreSQL/PostGIS y migraciones | Docker aislado y migraciones desechables; seis casos PostGIS incluidos en las 54 pruebas finales del 2026-11-15. Destino remoto aún pendiente |
| 3 | Catálogo versionado con fuente | HDX/CNIGS/OCHA: 721 territorios del lote fijado, polígonos, licencia y SHA-256 en `apps/api/data/SOURCE.json`; actualidad/piloto requieren validación local |
| 4 | Registro, correo, sesión y logout | API y UI; verificar pruebas automatizadas; **entrega real Resend pendiente** de dominio/credencial |
| 5 | Consulta anónima y sugerencia limitada | Búsqueda sin GPS; sugerencias sujetas a validación/rate limit; comprobar antiabuso en staging |
| 6 | GPS y pin de entrada | Solicitud por acción expresa; navegador y prueba funcional; hardware GPS real pendiente |
| 7 | Denegación GPS y flujo alternativo | Borrador/sugerencia no presencial, sin estado verificado; prueba negativa requerida |
| 8 | Calle y número opcionales | Formularios y validación API; verificar envío sin calle/número |
| 9 | Duplicados antes de publicar | Candidatos explicables y revisión; calibración con pares etiquetados del piloto pendiente |
| 10 | Moderación auditada | Autor diferente, rol servidor, motivo y registro de decisión; probar transiciones inválidas |
| 11 | Código estable y lectura pública | Publicación autorizada con código único; búsqueda/API solo de registros aprobados visibles |
| 12 | Fusión conserva referencias | Redirecciones y carrera recíproca verificadas: `200`/`422`, ambos códigos resuelven a la misma entidad canónica |
| 13 | Privacidad de vivienda/GPS | Pruebas negativas de lecturas públicas y whitelist Pydantic de address; campos privados adicionales no salen en DTO |
| 14 | Reportes y retirada | Endpoint público antiabuso y revisión de privacidad; verificar ocultación en buscador y ficha |
| 15 | API básica documentada | FastAPI OpenAPI y endpoints search/code/nearby/territories; pruebas de contrato |
| 16 | Claves con propiedad/cuota/revocación | Secreto una vez, hash persistido; comprobar dueño diferente, 401 y 429 |
| 17 | Entornos diferenciados | APP_ENV, DB explícita, secretos de producción y cookies seguras; validar arranque fail-closed |
| 18 | CI crítica | Full pytest local final del 2026-11-15: 54 pasan, 2 warnings, 84.30 s, incluidos seis casos PostGIS; Node web/Sites: 10 pasan. E2E de navegador comprobados manualmente en CUA, no automatizados en CI. Ejecución de Actions remoto pendiente: cuota no accesible; primer push omite CI para respetar presupuesto cero |
| 19 | Móvil/conexión lenta | Diseño adaptable; registrar inspección visual y fallos de red; prueba simulada a 390 px: 4,894 s antes y 2,589 s después de gzip, una navegación por caso; hardware/red móvil real pendiente |
| 20 | Kreyòl y francés | Selector y textos críticos; **revisión editorial por hablantes nativos pendiente** |
| 21 | Logs y recuperación | Backup sintético cifrado/restaurado: `docs/backup-roundtrip.json`. Custodia de claves, recuperación de objetos/datos reales, copias externas programadas y alertas remotas pendientes |
| 22 | Honestidad de métricas | No presentar demo como cobertura real ni tarifa de recompensa |
| 23 | Sin pagos reales | Dinero deshabilitado; no hay cobros, payouts ni promesas monetarias |
| 24 | Piloto territorial limitado | **Pendiente de selección de comuna, operadores locales y validación de negocio** |

## Fases futuras expresas del documento

No están habilitados: campañas de dinero, suscripciones comerciales cobradas, payouts, reputación certificada, compartición de residencias, navegación propia, PWA offline nacional ni importaciones indiscriminadas de POI. Activarlos requiere los contratos y controles indicados en el documento; no basta con conectar un proveedor de pagos.

## Uso de los servicios mencionados

| Servicio | Alcance actual |
| --- | --- |
| Resend | Adaptador de correo; requiere configuración y prueba de entrega real |
| Render | Blueprint de API; acceso remoto devolvió `UNAUTHORIZED`, sin desplegar |
| Vercel | Configuración web/proxy, sin desplegar y con origen `.invalid` a sustituir |
| Supabase | Opción de PostgreSQL/PostGIS dedicada; no se modifica ningún proyecto existente |
| GitHub | Repositorio privado creado y CI preparado; primer push con CI omitido hasta confirmar cuota gratuita |
| Stripe / PayPal | Sin operaciones financieras, coherente con exclusión del MVP |
| LottieFiles | Recurso opcional de presentación; ninguna animación reemplaza estados o funcionalidad verificable |

## Regla de cierre

La verificación Docker utiliza el proyecto `haiti-tracking-verify`, separado del arranque normal: DB `55433`, API `8002`, web `4174`. Ni ese entorno local ni el catálogo administrativo equivalen a cobertura de lugares verificados o a operación remota. El responsable de integración ejecutó la ronda completa final de 54 pruebas, con los controles de relaciones, alias, retiro, GPS, QR y contratos administrativos. Los límites operativos y de CI siguen abiertos.

El proyecto puede revisarse localmente sin declarar que satisface la certificación completa del piloto. La autorización de producción exige cerrar los puntos operativos pendientes, ejecutar las pruebas en su arquitectura real y conservar evidencia del mismo commit que se publicará. El informe de pruebas y seguridad final del trabajo prevalece para resultados efectivamente ejecutados; esta matriz no los inventa.
