# Haiti Tracking by Nexovax

**Documento maestro de producto, arquitectura y especificación funcional/técnica**  
**Versión:** 1.0 (base de planificación)  
**Fecha:** 14 de noviembre de 2026  
**Estado:** proyecto por desarrollar; no representa funcionalidades ya implementadas  
**Nombre del producto:** Haiti Tracking by Nexovax  
**Nombre del repositorio sugerido:** `Haiti-Tracking-by-Nexovax`  
**Ruta de trabajo prevista por el propietario:** `C:\Users\en-rr\Desktop\Haiti-Tracking-by-Nexovax`  
**Lema:** *Cada lugar de Haití merece una dirección.*

> **Naturaleza de este archivo:** es la especificación de un proyecto de software, no un prompt ni una orden de ejecución automática. Establece el producto que se quiere construir, sus reglas, límites, componentes, contratos, prioridades y criterios de aceptación. Las reglas funcionales reflejan la visión del producto discutida; las tecnologías, umbrales y estructuras recomendadas son decisiones iniciales propuestas, revisables mediante decisiones de arquitectura documentadas (ADR). Ningún dominio, métrica, tarifa o dato de ejemplo constituye un servicio real o una promesa comercial.

---

## 1. Resumen ejecutivo

**Haiti Tracking by Nexovax** es una plataforma colaborativa de direcciones digitales y datos geográficos para Haití. Permite que ciudadanos y colaboradores identifiquen, propongan, documenten y verifiquen establecimientos, lugares públicos, vías, puntos de referencia y accesos geográficos que son difíciles de localizar mediante direcciones convencionales.

Cada ubicación aprobada recibe un identificador digital único y estable (por ejemplo, `HT-NXV-000001`). Los lugares públicos y comerciales cuya difusión está permitida podrán buscarse en un mapa y consultarse mediante **Haiti Tracking API**, una API REST para desarrolladores, servicios de reparto, comercio electrónico, transporte, logística y sistemas de información.

La plataforma no debe limitarse a acumular pines: su diferenciador es la **calidad verificable de los datos**. El núcleo del sistema combina captura GPS presencial, confirmación visual del punto, clasificación territorial, detección de duplicados, revisión humana, reputación del colaborador, trazabilidad y protección de la privacidad.

Un programa de aportes recompensados podrá pagar por contribuciones de alto valor una vez verificadas y financiadas. Las recompensas no se otorgan automáticamente por enviar un formulario. Los registros residenciales privados requieren una política estricta y no se publican por defecto.

### 1.1 Problema que se quiere resolver

En diversas zonas de Haití, encontrar una dirección exacta puede depender de referencias verbales, nombres locales, hitos y conocimiento de personas de la comunidad. No siempre existen calle y número formalmente asignados o visibles. Esto dificulta entregas, visitas, comercio, transporte y servicios que necesitan llegar a una entrada concreta.

### 1.2 Propuesta de valor

- **Para ciudadanos:** buscar y compartir puntos registrados sin tener que explicar repetidamente cómo llegar.
- **Para colaboradores:** mejorar la información geográfica y obtener reconocimiento o incentivos cuando existan campañas de recompensas habilitadas.
- **Para comercios:** disponer de una ficha verificada, una coordenada de acceso y un código fácil de compartir.
- **Para desarrolladores:** consumir una API documentada de búsqueda, geocodificación, consulta por identificador y proximidad.
- **Para Nexovax:** operar una infraestructura de datos geográficos sostenible, con calidad, gobernanza y un modelo B2B.

### 1.3 Objetivos del MVP

1. Consultar un mapa y buscar ubicaciones públicas sin registro obligatorio.
2. Permitir sugerencias públicas limitadas sin cuenta (no verificadas) y crear una cuenta para contribuciones presenciales, verificar el correo y gestionar el perfil.
3. Capturar una posición real autorizada desde el dispositivo y registrar un punto de acceso en el mapa.
4. Guardar una propuesta geográfica estructurada para revisión.
5. Detectar posibles duplicados antes de crear la ubicación definitiva.
6. Aprobar, rechazar, fusionar o solicitar correcciones desde un panel administrativo.
7. Publicar exclusivamente registros que cumplan las reglas de seguridad y privacidad.
8. Emitir códigos únicos estables y permitir su resolución.
9. Exponer una API REST v1 documentada y protegida por claves.
10. Registrar procedencia, cambios, validaciones y métricas técnicas.

### 1.4 Indicadores iniciales de éxito

Los valores objetivo deben decidirse después del piloto; no deben presentarse números inventados como resultados reales.

| KPI | Definición | Cómo medir |
| --- | --- | --- |
| Cobertura | Lugares verificados por comuna o zona priorizada | Conteo de ubicaciones públicas aprobadas por área |
| Calidad | Proporción de aportes aceptados tras verificación | Aprobados / evaluados |
| Duplicación | Registros fusionados o rechazados como duplicados | Eventos de deduplicación |
| Actualidad | Antigüedad de la última verificación | Histograma de `last_verified_at` |
| Utilidad | Búsquedas que terminan con apertura de ficha o copia de código | Eventos agregados sin rastreo personal invasivo |
| Latencia API | p50/p95 de consultas de búsqueda y por código | Métricas de servidor |
| Confiabilidad | Errores de API y disponibilidad | Monitorización |
| Seguridad | Incidentes de fuga de ubicación privada | Debe mantenerse en cero; respuesta e investigación |

---

## 2. Principios del producto y reglas no negociables

**P-01. Precisión con honestidad.** Una coordenada GPS no demuestra por sí sola que el lugar está correctamente identificado. Se registra precisión estimada, procedencia y estado de validación.

**P-02. Privacidad desde el diseño.** Una vivienda privada no es un punto de interés público. Su ubicación exacta nunca se indexa ni expone por defecto. Compartirla requiere control de la persona autorizada.

**P-03. GPS requerido para un aporte presencial verificable.** La aplicación solicita permiso de geolocalización solo al iniciar el flujo correspondiente; no puede forzar el permiso del navegador. Sin geolocalización autorizada no hay envío como *aporte presencial verificado*, ni incentivo asociado. Consultar el mapa no exige GPS.

**P-04. Identificador único estable.** Una ubicación verificada tiene un identificador que no cambia al corregir su nombre o dirección. Las fusiones conservan redirección o alias desde los códigos antiguos.

**P-05. No duplicar artificialmente.** Dos puntos cercanos pueden ser distintos si son entradas, viviendas, negocios o unidades legítimas. Proximidad no equivale a identidad.

**P-06. Verificación y control humano.** La automatización propone; no publica ubicaciones ambiguas ni autoriza pagos de manera incondicional.

**P-07. Trazabilidad.** Cambios, fuentes, decisiones de revisión y transacciones económicas deben quedar auditados.

**P-08. Inclusión geográfica.** Calle y número son opcionales cuando no existen; referencias locales, secciones comunales y puntos de acceso son fundamentales.

**P-09. Accesibilidad lingüística.** El producto público prioriza **kreyòl ayisyen** y **français**; español e inglés pueden añadirse. Los nombres originales y sus variantes se preservan.

**P-10. No vender promesas.** Las recompensas económicas y planes comerciales solo se habilitan cuando existan reglas, capacidad de pago, cumplimiento y contratos operativos.

**P-11. API segura y predecible.** Ninguna ruta de consulta pública revela borradores, observaciones GPS, datos privados o evidencia sensible.

**P-12. Licencias y procedencia.** Los datos importados preservan fuente, fecha y licencia; no se reutiliza información obtenida de mapas o bases incompatibles con sus condiciones.

---

## 3. Personas usuarias, roles y permisos

### 3.1 Roles de negocio

| Rol | Puede hacer | Restricciones |
| --- | --- | --- |
| Visitante | Ver mapa, buscar, consultar fichas públicas, copiar código y enviar una sugerencia limitada | No enviar aportes verificados, no cobrar recompensas ni ver datos protegidos |
| Usuario registrado | Gestionar perfil, sugerir información, reportar errores | No aprobar su propio aporte |
| Colaborador | Presentar aportes presenciales con GPS, gestionar historial, sugerir correcciones | Sin publicación automática ni recompensa garantizada |
| Verificador comunitario | Evaluar casos asignados, confirmar referencias, marcar inconsistencias | No decidir casos con conflicto de interés ni liberar pagos |
| Moderador | Revisar aportes, pedir cambios, resolver duplicados y reportes | Acceso mínimo necesario; acciones auditadas |
| Administrador | Gestionar territorios, usuarios, categorías, políticas, campañas y moderación | MFA, privilegios delimitados, auditoría completa |
| Gestor financiero | Revisar saldos aprobados, lotes y conciliaciones de pagos | No puede crear y aprobar unilateralmente una recompensa |
| Desarrollador | Crear aplicaciones, claves API y ver consumo | Solo recursos públicos o expresamente autorizados |
| Empresa | Administrar aplicación, miembros, facturación y uso API | No accede a ubicaciones privadas sin permiso delegado |
| Titular de una residencia | Autorizar y revocar divulgación puntual de su propia ubicación | Debe demostrar control de la ubicación; nunca se presume por estar cerca |

### 3.2 Autenticación y autorización

- Acceso web mediante sesiones seguras con cookies `HttpOnly`, `Secure`, `SameSite`, protección CSRF según arquitectura y expiración controlada.
- Contraseñas almacenadas usando **Argon2id**, nunca en texto claro.
- Verificación de correo antes de acciones que requieran confianza; teléfono como segundo medio opcional según despliegue.
- MFA obligatorio para administradores y recomendable para moderadores y pagos.
- Control de acceso por roles y permisos finos; las comprobaciones se realizan en backend, no solo en interfaz.
- Las API keys de aplicaciones B2B se crean y rotan desde el portal de desarrolladores; el secreto solo se muestra una vez y se almacena con hash.
- Prohibido usar claves API secretas en JavaScript público o aplicaciones móviles distribuidas. Para clientes públicos se requiere un proxy propio o credenciales restringidas y controladas.
- No confundir credenciales de usuario, de aplicación, de personal administrativo y tokens temporales para compartir residencias.

---

## 4. Alcance y fases

### Fase 0 — Fundaciones

- Repositorio, estructura de monorepo, entornos, convenciones de código y CI.
- Modelo de datos, migraciones, PostgreSQL/PostGIS, seed de territorios con procedencia.
- Autenticación, permisos, seguridad básica, diseño responsivo, internacionalización.
- Proveedor cartográfico elegido según licencia y presupuesto.

### Fase 1 — MVP de datos verificables

- Inicio, mapa público, búsqueda de lugares aprobados, sugerencias anónimas limitadas con protección antiabuso y fichas con código.
- Registro y acceso de usuarios; perfil e historial de contribuciones.
- Formulario de aporte presencial con permiso GPS, pin y referencias.
- Comprobación de duplicados por proximidad y texto.
- Estados de propuesta y revisión administrativa.
- Publicación únicamente de lugares públicos/comerciales autorizados.
- API básica: búsqueda, ubicación por código, cercanos y territorios.
- Auditoría, reportes de errores y pruebas automatizadas.

### Fase 2 — Calidad comunitaria

- Verificaciones cruzadas, reputación, revisión por zonas, edición y versionado.
- Mejor búsqueda por alias y variantes lingüísticas.
- Fotografías revisadas, reportes de cambios, panel de calidad.
- Programa piloto de incentivos **sin pagos automáticos**, financiado y controlado.

### Fase 3 — API comercial

- Portal de desarrolladores, gestión de proyectos y claves API.
- Métricas por aplicación, planes Free/Pro/Enterprise, cuotas y facturación.
- Geocodificación, geocodificación inversa, mejores filtros y SDKs.
- Contratos, webhooks opcionales y soporte empresarial.

### Fase 4 — Escalamiento

- Expansión nacional según cobertura y calidad.
- Cliente móvil/PWA con captura diferida para áreas de conexión limitada.
- Sistema residencial privado basado en autorizaciones y códigos temporales.
- Integración con motores externos de rutas y logística, **no** desarrollo de navegación propia desde cero.

### Fuera de alcance inicial

- Rutas turn-by-turn, cálculo propio de tráfico, predicción de ETA o cartografía vial nacional desde cero.
- Publicar residencias privadas por colaboración de terceros.
- Vender perfiles personales o historiales de movimientos de usuarios.
- Transferencias automáticas de dinero sin integraciones y revisión legal/operativa.
- Prometer que un GPS web prueba presencia física contra manipulaciones sofisticadas.
- Importar indiscriminadamente puntos de servicios de mapas de terceros.

---

## 5. Historias de usuario y flujos esenciales

### HU-01 — Buscar una dirección

**Dado** un visitante en el inicio, **cuando** escribe nombre, referencia o código, **entonces** ve coincidencias públicas clasificadas y puede abrir la ficha con mapa, categoría, nivel de confianza, última revisión y código para compartir. Si la consulta no tiene resultados, recibe alternativas y una invitación a sugerir una ubicación.

### HU-02 — Registrar una cuenta

Un visitante puede comunicar una sugerencia básica de lugar público sin crear cuenta, sujeta a CAPTCHA/rate limit y revisión; no se publica automáticamente ni genera recompensa. Para registrar aportes presenciales verificados y acceder a recompensas es obligatoria la cuenta.

El usuario proporciona nombre, correo, teléfono opcional y contraseña; acepta los términos aplicables y verifica su correo. Puede indicar intención de colaborar, utilizar la API o representar una empresa; estos son perfiles de uso, no permisos elevados automáticos.

### HU-03 — Contribuir presencialmente

El colaborador inicia sesión, selecciona «Registrar ubicación», concede acceso temporal al GPS, confirma el acceso real en el mapa, completa territorio y descripción, acepta la declaración de procedencia y ejecuta comprobación de duplicados antes del envío.

### HU-04 — Detectar duplicado antes de enviar

Si existe una coincidencia probable, el sistema muestra puntos similares con nombre, categoría, distancia aproximada y acción de corregir o confirmar. Si el aporte parece representar un negocio diferente en el mismo inmueble, permite continuar con justificación y lo marca para revisión.

### HU-05 — Revisar la propuesta

Un moderador ve propuestas en una bandeja, evidencia autorizada, riesgos y coincidencias. Puede `approve`, `reject`, `request_changes` o `merge`. Cada decisión requiere un motivo y genera registro de auditoría.

### HU-06 — Consumir la API

Un desarrollador crea una aplicación, obtiene una credencial de servidor, consulta `/v1/locations/search` y recibe JSON documentado con las ubicaciones **públicas** aprobadas. El sistema aplica cuota, autenticación, trazabilidad y errores normalizados.

### HU-07 — Corregir una ubicación ya aprobada

El usuario no sobrescribe directamente la ficha publicada: presenta una propuesta de modificación enlazada al `location_id`. El personal valida el cambio conservando historial, identificador y atribución.

### HU-08 — Compartir residencia (fase posterior)

El titular autorizado crea un enlace/código temporal, con expiración, propósito y revocación. El destinatario solo consulta el punto permitido mientras esté vigente. Los detalles no se indexan públicamente ni se muestran en el mapa general.

### HU-09 — Recompensa (piloto posterior)

Una contribución aprobada puede resultar elegible para una campaña vigente; el sistema genera una transacción **pendiente**. Solo después de la revisión antifraude, condiciones de campaña y autorización financiera se convierte en saldo pagable. Ninguna simple propuesta crea dinero exigible.

---

## 6. Experiencia de usuario y mapa de pantallas

### 6.1 Identidad y estilo visual

Inspiración en la propuesta visual ya explorada: estética SaaS moderna, interfaces claras, tarjetas con bordes redondeados y sombras discretas; azul oscuro y azul vivo como base, blanco como fondo principal, rojo haitiano como acento de acciones; verde solo para estados validados. Debe funcionar bien en móviles de gama media y con conexiones lentas. No utilizar contadores de usuarios o consultas ficticias como estadísticas reales.

**Navegación principal:** `Inicio` · `Mapa` · `Contribuir` · `API` · `Entrar / Mi cuenta`.

### 6.2 Pantallas obligatorias

| Ruta web sugerida | Pantalla | Contenido imprescindible |
| --- | --- | --- |
| `/` | Inicio | Propuesta de valor, buscador, mapa resumido, cómo funciona, CTA aportar/consultar API |
| `/mapa` | Mapa público | Mapa, búsqueda, filtros por territorio/categoría, resultados, fichas autorizadas |
| `/ubicaciones/[codigo]` | Ficha pública | Nombre, ubicación, punto de acceso, dirección estructurada, referencias, código, enlace/QR, nivel de confianza, última verificación, reportar error |
| `/registro` | Crear cuenta | Nombre, correo, teléfono opcional, contraseña, confirmación, perfil de uso, consentimientos |
| `/acceso` | Acceso | Login, recuperación segura, verificación de correo |
| `/contribuir/nueva` | Nueva propuesta | GPS, mapa, formulario de datos, duplicados, evidencia, privacidad, revisión previa |
| `/contribuciones` | Mis propuestas | Estados, historial, mensajes de revisión y correcciones |
| `/cuenta` | Perfil y privacidad | Datos propios, sesiones, consentimiento, eliminación y exportación donde aplique |
| `/desarrolladores` | Presentación API | Capacidades, guías, documentación, acceso a portal |
| `/desarrolladores/panel` | Panel API | Apps, claves, cuotas, ejemplos y consumo |
| `/admin` | Resumen administrativo | Propuestas por estado, alertas, reportes, cobertura y métricas |
| `/admin/revision` | Bandeja de revisión | Comparación en mapa, candidatos duplicados, evidencia, acciones de moderación |
| `/admin/territorios` | Catálogo territorial | Importación, alias, fuente, edición controlada y versión |
| `/admin/auditoria` | Auditoría | Historial protegido y búsquedas por actor/objeto/acción |
| `/legal/*` | Avisos legales | Términos, privacidad, política de aportes, reglas de publicación |

### 6.3 Formulario detallado de nueva ubicación

Dividir el formulario en pasos para facilitar uso móvil. El usuario podrá guardar borradores, pero un borrador no es un registro verificado.

**Paso A: confirmar presencia y punto**

- Botón `Activar ubicación` que solicita permiso solo cuando el usuario lo pulsa.
- `latitude`, `longitude`, `accuracy_m`, `captured_at` y tipo de fuente entregado por la API del dispositivo cuando exista.
- `enableHighAccuracy: true`, `maximumAge: 0`; tiempos de espera y reintentos controlados.
- Mapa con punto del dispositivo y marcador de la **entrada/acceso real**; el ajuste manual no debe modificar silenciosamente la lectura original del GPS.
- Distancia entre GPS observado y marcador seleccionado; pedir explicación y revisión especial si es alta.
- Si no hay permisos o señal suficiente, explicar el motivo y permitir guardar borrador o propuesta no verificada **sin elegibilidad para recompensa presencial**.

**Paso B: clasificación y territorio**

- Tipo de lugar: `public_place`, `business`, `landmark`, `building_entrance`, `road_reference`, `private_residence` (este último sigue flujo privado diferenciado; no se publica).
- Departamento, arrondissement si aplica al dataset, comuna, sección comunal si aplica, barrio/zona/localidad.
- Nombre principal del lugar o descripción identificadora según categoría.
- Calle/camino y número **opcionales** si no existen.
- Piso, unidad, bloque o entrada adicionales (solo cuando correspondan; tratar como información sensible si identifican vivienda).
- Punto de referencia local, indicaciones de acceso y alias en kreyòl/francés.
- Campos mínimos por categoría; no exigir `street`, `house_number` ni nombre comercial a una referencia natural.

**Paso C: evidencia y procedencia**

- Descripción breve en idioma local; fuente del conocimiento (observación propia, responsable del local, referencia comunitaria).
- Fotografías opcionales de fachadas o letreros para lugares **no residenciales**, sujetas a moderación, control EXIF y permisos de publicación.
- Casilla que declara que el colaborador está autorizado a compartir la información presentada.
- Prohibición de subir fotografías de documentos de identidad, menores, interiores de residencias o datos que puedan vulnerar la privacidad.

**Paso D: comprobación y envío**

- Mostrar coincidencias geográficas y textuales.
- Permitir acciones `Es este lugar`, `Proponer corrección`, `Es un lugar distinto` con justificación.
- Resumen final y botón `Enviar para verificación`.
- Respuesta con número de contribución, estado y fecha, **sin prometer dinero**.

### 6.4 Estados visibles en la interfaz

- `draft` — guardado por el autor; solo él lo ve.
- `submitted` — recibido y pendiente.
- `needs_review` — requiere revisión adicional.
- `changes_requested` — se solicitaron correcciones.
- `approved` — validado; publicación depende de política de visibilidad.
- `rejected` — no aprobado, con motivo.
- `merged` — se consolidó con una ubicación existente.
- `withdrawn` — retirado por el autor antes de una decisión cuando sea posible.

### 6.5 UX, accesibilidad y conectividad

- Internacionalización desde el inicio con `ht` (kreyòl), `fr` (francés); `es` opcional para equipo y `en` futuro.
- Conservar el texto original y un campo de búsqueda normalizado; no traducir automáticamente nombres propios sin revisión.
- Cumplimiento objetivo WCAG 2.2 AA en flujos críticos: navegación por teclado, contraste, foco, etiquetas, errores accesibles, alternativas textuales al mapa.
- El punto seleccionado debe poder revisarse mediante coordenadas y controles accesibles, no solo arrastrar con el dedo.
- PWA y borradores locales cifrados/protegidos como mejora posterior; nunca almacenar GPS o información residencial sensible sin medidas de seguridad.
- Evitar fotos pesadas, usar carga diferida y compresión apropiada; estados de carga y reintentos claros.

### 6.6 Referencia visual existente (orientativa)

Existe un mockup previo llamado `interfaz_haiti_tracking_mapa_y_contribuciones.png`, con tres vistas ilustrativas: inicio/mapa, creación de cuenta y formulario de aportes. Si se copia al repositorio puede almacenarse en `docs/product/assets/`. **El presente documento es autosuficiente si falta esa imagen**; el diseño final debe corregir cualquier estadística o tarifa ficticia mostrada en el concepto y respetar permisos de GPS y privacidad descritos aquí. No se considera una interfaz programada.

---

## 7. Modelo territorial y semántica de direcciones

### 7.1 Jerarquía territorial

El sistema representa la realidad administrativa y los nombres de uso local. Modelo conceptual:

`País (HT) -> Departamento -> Arrondissement (si aplica) -> Comuna -> Sección comunal (si aplica) -> localidad/barrio/zona -> vía/camino -> edificio/entrada/unidad`.

**Importante:** arrondissement y sección comunal no deben imponerse a todas las formas de dirección como campos obligatorios. Algunas fuentes oficiales organizan los límites para intercambio de datos con niveles ligeramente diferentes. Los recuentos administrativos pueden variar por publicación o fecha; **no programar números fijos de comunas/secciones**. Elegir un catálogo base versionado con fuente verificable, guardar `source_code` o `pcode`, soportar alias y revisiones territoriales.

### 7.2 Tipos de punto geográfico

- `point_of_interest`: entidad (escuela, hospital, negocio, plaza).
- `access_point`: entrada física a un inmueble o establecimiento; puede ser más útil para entrega que el centroide.
- `building`: edificio que puede contener varias unidades.
- `road_reference`: referencia de vía/camino.
- `landmark`: elemento comunitario de orientación.
- `private_address`: residencia protegida, separada del catálogo público.

No asignar el mismo código a lugares distintos solo por compartir coordenadas. Un complejo comercial puede contener varios negocios y varias entradas, por lo que se modelan relaciones `parent_location_id`, `access_point_id` y, si procede, `unit_label`.

### 7.3 Identificador digital

- Identificador interno: `UUID`.
- Código público estable: `HT-NXV-` + secuencia con mínimo seis cifras, por ejemplo `HT-NXV-000001`; formato sujeto a evolución sin perder compatibilidad.
- Una vez publicado, el código no se recicla.
- Si se fusionan entidades, el código de la duplicada apunta a la canónica mediante tabla de redirecciones, con respuesta explícita `canonical_code`.
- Para fichas públicas, generar URL compartible y QR que apunten al código público; no incluir información privada incrustada en el QR.
- Nunca inferir privilegios de acceso a partir de conocer el código.
- Los códigos privados siguen un mecanismo separado y no son enumerables públicamente.

### 7.4 Datos de precisión y confianza

Distinguir siempre:

- **Posición observada (`gps_observation`)**: lo que informa el dispositivo del colaborador en el momento de la captura.
- **Punto elegido (`selected_point`)**: la entrada/acceso que la persona identifica en el mapa.
- **Punto canónico (`location.point`)**: el punto aprobado como referencia pública, si corresponde.
- **Exactitud informada (`accuracy_m`)**: estimación de error del dispositivo, no garantía de exactitud física.
- **Confianza (`confidence_score`)**: evaluación del sistema y revisores, de 0 a 1, separada de la precisión GPS.

---

## 8. GPS: política obligatoria para aportes presenciales

### 8.1 Decisión funcional

- **No exigir GPS para navegar, buscar o consumir la API.**
- **Sí solicitar GPS para intentar registrar una contribución presencial verificable y elegible para futuras recompensas.**
- La persona puede denegar el permiso; en ese caso no se puede completar el flujo presencial, pero se ofrece explicación, borrador o sugerencia no verificada, sin engañar al usuario.
- Las aplicaciones web no pueden activar GPS del sistema a la fuerza. La solicitud requiere permiso expreso y generalmente HTTPS; la precisión depende del dispositivo y entorno.
- No activar seguimiento permanente ni recopilar movimientos. Obtener solo lecturas necesarias para la tarea actual.

### 8.2 Algoritmo inicial de captura

1. Al pulsar `Usar mi ubicación`, llamar a Geolocation API en HTTPS con alta precisión solicitada, `maximumAge = 0` y timeout configurable.
2. Si falla por permiso denegado, timeout o indisponibilidad, mostrar el motivo y opción de reintento o borrador.
3. Si llega una lectura, capturar coordenadas, `accuracy`, timestamp y `source = browser_geolocation`.
4. Mostrar círculo de precisión y marcador del dispositivo. Permitir refrescar para obtener una mejor lectura.
5. Pedir confirmación del **punto de acceso** real; si el pin se ajusta, conservar ambos puntos y diferencia en metros.
6. Aplicar reglas de precisión configurables por región/tipo de lugar. Umbrales sugeridos del piloto: `<= 30 m` buena señal; `> 30 y <= 100 m` revisión reforzada; `> 100 m` no aprobar como evidencia presencial suficiente sin otra prueba. **Son parámetros iniciales, no estándares universales.**
7. Rechazar valores fuera de rangos válidos, timestamps imposibles y lecturas inverosímiles; no confiar en la hora del cliente ni declarar imposible el spoofing.
8. Realizar deduplicación y revisión antes de publicar.
9. Minimizar y depurar lecturas sensibles según política de retención, sin mostrar coordenadas de la observación en APIs públicas.

### 8.3 Comprobaciones adicionales

- Señalar discrepancia si el GPS observado está muy lejos del marcador propuesto.
- Comparar territorio seleccionado con el punto cartográfico y pedir confirmación ante desacuerdos.
- Detectar ráfagas de registros, coincidencias de dispositivo/cuentas cuando exista base legal y consentimiento, patrones repetitivos y fotos reutilizadas.
- Evitar castigar automáticamente zonas donde la recepción sea limitada; mandar a revisión y ofrecer otros métodos de evidencia.
- Para fraude complejo de GPS se requiere verificación multifactor y moderación; un navegador no brinda prueba criptográfica de presencia física.

---

## 9. Detección y resolución de duplicados

### 9.1 Requisito

Una contribución nueva **debe** pasar por detección de duplicados antes de crear una ubicación canónica. El resultado es una lista de candidatos, no solo un booleano.

### 9.2 Señales

1. **Distancia espacial**: buscar candidatos con PostGIS `ST_DWithin(...::geography, ..., radio_metros)` y ordenar por distancia.
2. **Territorio**: departamento, comuna, sección, barrio, teniendo en cuenta límites y alias.
3. **Texto**: normalizar mayúsculas, acentos, abreviaturas (`Rue` / `R.`), puntuación, variantes de escritura y kreyòl/francés; similitud trigram (`pg_trgm`) y, más adelante, búsqueda fonética o embeddings controlados.
4. **Categoría**: dos farmacias con nombres similares merecen mayor atención; una tienda y un hospital en la misma parcela no son automáticamente iguales.
5. **Identificadores y relaciones**: número de unidad, planta, nombre comercial, `parent_location_id`, entrada diferenciada.
6. **Evidencia**: fotos y relaciones aportadas por moderadores; no usar reconocimiento biométrico de personas.

### 9.3 Scoring inicial (propuesta, no valor científico)

`score = 0.35 * proximity + 0.30 * name_similarity + 0.15 * territory_match + 0.10 * category_match + 0.10 * address_reference_match`

Cada subfactor se normaliza a `[0, 1]`. Umbrales configurables tras medir datos del piloto:

- `>= 0.85`: coincidencia fuerte. Detener publicación automática y proponer actualización/fusión.
- `0.60 a < 0.85`: revisar manualmente.
- `< 0.60`: candidato débil; permitir avanzar con revisión normal.

**Excepciones:** mismo inmueble con negocios distintos, varias entradas, unidades y puntos de referencia no se fusionan por puntaje sin análisis de identidad.

### 9.4 Flujo de resolución

- Mostrar 3–10 candidatos y explicaciones legibles (`a 35 m`, `nombre parecido`, `misma comuna`).
- Permitir `es_mismo_lugar`, `es_diferente`, `proponer_actualizacion`.
- Bloquear la consolidación física mientras un moderador resuelve conflicto.
- Al fusionar, conservar código antiguo como alias, versiones previas, auditoría y autoría de aportes.
- Una operación de alta debe ser transaccional e idempotente; usar índices, bloqueos/constraint apropiado y comprobar nuevamente duplicados al aprobar para evitar carreras simultáneas.
- Crear pruebas que verifiquen tanto falsos positivos como falsos negativos.

---

## 10. Verificación, moderación y calidad

### 10.1 Máquina de estados de contribución

```text
draft -> submitted -> needs_review -> approved
                  |               -> changes_requested -> submitted
                  |               -> rejected
                  |               -> merged
                  -> withdrawn (cuando proceda)
```

La ubicación canónica publicada maneja su ciclo independiente: `active`, `under_review`, `hidden`, `retired`, `merged`. No equiparar propuesta aprobada con publicación para todos los tipos de datos.

### 10.2 Reglas de validación

- Campos obligatorios según categoría completos y coherentes.
- Coordenadas válidas, con precisión y metadatos de observación cuando es aporte presencial.
- No existe duplicado no resuelto de alta probabilidad.
- La revisión evalúa calidad, correspondencia territorial, referencia, evidencia y permisos.
- Las residencias privadas no entran en el buscador público, aunque se haya aceptado su captura privada.
- No permitir que el autor apruebe su propio aporte ni que un verificador con conflicto de interés marque una recompensa como pagable.
- Motivo obligatorio al rechazar, fusionar, ocultar o editar datos sensibles.
- Las fichas públicas muestran `verification_status`, `confidence_score` y `last_verified_at`, pero no el historial personal del colaborador.

### 10.3 Reputación (fase 2)

Puntuar calidad histórica, corroboración independiente, correcciones útiles y sanciones verificadas. No asignar autoridad ilimitada por volumen. Los pesos y penalizaciones deben ser explicables y apelables. El nivel de confianza de una ubicación no es lo mismo que la reputación de su autor.

### 10.4 Reportes

Cualquier persona puede reportar dirección incorrecta, duplicado, cierre de negocio, exposición de datos privados o contenido indebido. Reportes de privacidad críticos priorizan ocultación temporal mientras se investiga. Se registra resultado de investigación con mínima información personal.

---

## 11. Incentivos, recompensas y pagos (no incluir como pago activo en el MVP)

### 11.1 Modelo de incentivos

Las contribuciones pueden ganar **puntos no monetarios** desde etapas tempranas. Las recompensas en dinero se activan únicamente en campañas expresamente financiadas, con reglas publicadas y revisadas. El prototipo visual anterior mostraba una cifra ilustrativa: **no se debe incorporar como tarifa real ni garantizar monto por ubicación**.

### 11.2 Requisitos previos a pagos reales

- Campaña con presupuesto, zona, tareas elegibles, límites, fechas y fórmula de cálculo.
- Identidad y elegibilidad del colaborador verificadas conforme al proveedor y normas aplicables.
- Confirmación independiente y antifraude.
- Libro mayor inmutable o de entradas compensatorias: `pending`, `approved`, `payable`, `paid`, `reversed`.
- Límite de desembolso, aprobación dual, conciliación y mecanismo de disputa.
- Proveedor de pago compatible con Haití y moneda HTG validado antes del lanzamiento.
- Revisión legal/fiscal y política de retenciones/consentimientos; no asumir regulación específica sin asesoría.

### 11.3 Causas de no elegibilidad

Duplicado existente, aporte falso, evidencia reciclada, ubicación privada sin consentimiento, múltiples cuentas manipuladas, datos imposibles, contribución fuera de campaña, autocertificación o violación de reglas.

### 11.4 Protección financiera

Nunca derivar saldos directamente de contadores en la interfaz. Toda obligación económica tiene transacción auditada y estado; operaciones de pago son idempotentes y reconciliables. No almacenar información bancaria sensible si un procesador puede tokenizarla.

---
## 12. Haiti Tracking API — contrato funcional v1

### 12.1 Objetivo de la API

Proporcionar a clientes autorizados datos estructurados y verificables sobre **lugares públicos/comerciales publicados**. La API no equivale a un motor de rutas. Los desarrolladores pueden utilizar los puntos devueltos en sistemas de reparto, catálogos, mapas y motores de navegación externos compatibles.

**URL de producción sugerida (no activa):** `https://api.haititracking.com/v1`  
**URL local de desarrollo propuesta:** `http://localhost:8000/v1`  
**Documentación OpenAPI local propuesta:** `http://localhost:8000/docs`  
**Formato:** JSON UTF-8, HTTPS obligatorio en producción  
**Versión:** prefijo mayor `/v1`, contratos publicados por OpenAPI 3.1  
**Referencias de fecha:** ISO 8601 con zona horaria UTC  
**Coordenadas:** EPSG:4326 (WGS84); en pares `latitude`/`longitude` se especifica la clave, en GeoJSON el orden es `[longitude, latitude]`.

### 12.2 Recursos y endpoints

| Método | Ruta | Acceso | Resultado |
| --- | --- | --- | --- |
| `GET` | `/v1/health` | infraestructura | Estado básico de servicio, sin datos internos |
| `GET` | `/v1/locations/search` | API key / web pública a través de backend | Buscar por texto, código, categoría y territorio |
| `GET` | `/v1/locations/{code}` | API key / web pública a través de backend | Obtener ficha pública por código y redirección canónica si fue fusionada |
| `GET` | `/v1/locations/nearby` | API key | Consultar puntos publicados en un radio |
| `GET` | `/v1/geocode` | API key | Resolver texto a una lista de puntos candidatos |
| `GET` | `/v1/reverse` | API key | Resolver coordenadas a referencias públicas y territorio, sin divulgar viviendas |
| `GET` | `/v1/territories` | API key / web | Catálogo jerárquico y búsqueda territorial |
| `GET` | `/v1/territories/{id}/children` | API key / web | Subdivisiones y alias |
| `POST` | `/v1/public-suggestions` | visitante, con CAPTCHA/rate limit | Recibir sugerencia limitada sobre lugar no residencial, siempre no verificada |
| `POST` | `/v1/contributions/check-duplicates` | sesión de colaborador | Simular candidatos duplicados antes del envío |
| `POST` | `/v1/contributions` | sesión de colaborador | Crear propuesta, no ubicación publicada |
| `GET` | `/v1/me/contributions` | sesión de colaborador | Historial propio |
| `GET` | `/v1/me/contributions/{id}` | autor o personal autorizado | Propuesta y motivo de revisión |
| `PATCH` | `/v1/me/contributions/{id}` | autor, solo estado editable | Corregir borrador o propuesta devuelta |
| `POST` | `/v1/locations/{code}/reports` | público con controles antiabuso | Reportar error, duplicado, privacidad o cierre |
| `GET` | `/v1/developer/apps` | sesión de desarrollador | Proyectos e información agregada de uso |
| `POST` | `/v1/developer/apps` | sesión de desarrollador | Crear app con cuota inicial |
| `POST` | `/v1/developer/apps/{id}/keys` | titular de la app, con reautenticación si procede | Emitir clave y mostrar secreto una vez |
| `POST` | `/v1/developer/apps/{id}/keys/{key_id}/revoke` | titular autorizado | Revocar clave |
| `GET` | `/v1/developer/apps/{id}/usage` | titular autorizado | Consumo por periodo, sin PII |
| `GET` | `/v1/admin/contributions` | moderador/admin | Bandeja segura de revisión |
| `POST` | `/v1/admin/contributions/{id}/decision` | moderador/admin con permisos | Resolver propuesta, motivo y auditoría |
| `POST` | `/v1/admin/locations/{id}/merge` | moderador/admin con permisos | Fusionar dos lugares y guardar redirecciones |

Los endpoints de administración y pagos no se exponen como API abierta a terceros. Para `GET` de portal público se puede utilizar backend propio con cuota y caché; no publicar una clave secreta en el navegador.

### 12.3 Autorización API B2B

- Clave de servidor en `Authorization: Bearer <HAITI_TRACKING_API_KEY>`.
- El token se valida por hash y se asocia a aplicación, titular, estado, permisos, límite y fecha de rotación.
- Diferenciar entorno `test` y `live`; secretos tienen prefijos reconocibles, pero el prefijo no reemplaza validación.
- Aplicar rate limit por app, clave, IP y ruta con respuestas `429` y `Retry-After`.
- No devolver en errores tokens, GPS de colaboradores, correos u otra información sensible.
- Ofrecer revocación inmediata, rotación segura, auditoría de creación/uso anómalo.
- El rol desarrollador no habilita lectura de residencias privadas.

### 12.4 Reglas comunes

- Filtros validados de manera estricta. Para radios usar metros y máximo configurable; bloquear extracciones masivas no autorizadas.
- Paginación por cursor: `limit` por defecto 20 y máximo inicial 50; `next_cursor` opaco. No permitir extracción ilimitada por un parámetro grande.
- Orden de resultados determinista; por relevancia en búsqueda, por distancia en cercanos.
- Fechas de actualización e indicador de verificación legibles.
- Preferir respuesta `200` para lectura, `201` para contribución creada pendiente de revisión, `202` para tareas de procesamiento diferidas.
- Documentar deprecaciones, cambios de versión y una política de compatibilidad.
- Códigos de error consistentes; identificador `request_id` para soporte.
- Sanitizar textos y aplicar límites de tamaño, validación y caracteres Unicode.
- Implementar `Idempotency-Key` para `POST` mutables críticos, en especial creación de propuesta y pagos.

### 12.5 API de búsqueda — ejemplo

**Solicitud:**

```http
GET /v1/locations/search?q=pharmacie%20delmas&limit=10 HTTP/1.1
Host: api.haititracking.com
Authorization: Bearer <API_KEY>
```

**Respuesta ilustrativa. Todos los nombres, códigos y coordenadas siguientes son ficticios:**

```json
{
  "success": true,
  "data": [
    {
      "code": "HT-NXV-000001",
      "name": "Pharmacie Démo",
      "type": "business",
      "address": {
        "country_code": "HT",
        "department": "Ouest",
        "commune": "Delmas",
        "neighborhood": "Delmas - secteur de démonstration",
        "street": null,
        "house_number": null,
        "reference": "Referencia ficticia de demostración"
      },
      "coordinates": {
        "latitude": 18.54,
        "longitude": -72.30
      },
      "verification_status": "verified",
      "confidence_score": 0.95,
      "last_verified_at": "2026-01-01T00:00:00Z"
    }
  ],
  "pagination": {
    "limit": 10,
    "next_cursor": null
  },
  "request_id": "req_demo_001"
}
```

**Invariantes:** la respuesta nunca contiene `contributor_user_id`, `gps_observations`, motivos internos de moderación, fotos privadas o ubicación residencial protegida.

### 12.6 Consulta por código y fusión

```http
GET /v1/locations/HT-NXV-000001 HTTP/1.1
Authorization: Bearer <API_KEY>
```

Si el código fue fusionado, devolver la ficha de la entidad canónica con `requested_code`, `canonical_code` y `was_redirected: true`, manteniendo semántica estable. Nunca utilizar este mecanismo para revelar códigos privados.

### 12.7 Lugares cercanos

```http
GET /v1/locations/nearby?lat=18.54&lon=-72.30&radius_m=500&limit=20 HTTP/1.1
Authorization: Bearer <API_KEY>
```

Validar latitud `[-90,90]`, longitud `[-180,180]`, radio positivo y dentro de límites del plan. Devolver distancia calculada desde el punto de consulta y solo recursos públicos aprobados.

### 12.8 Geocodificación / geocodificación inversa

- `GET /v1/geocode?q=...&commune_id=...` devuelve **lista de candidatos** con `match_type` y `confidence_score`; no afirmar una coincidencia exacta si es ambigua.
- `GET /v1/reverse?lat=...&lon=...` devuelve la zona administrativa y lugares públicos cercanos con distancia. No deducir ni divulgar la vivienda de una persona a partir del punto.
- Diferenciar coincidencia textual/geográfica de posición físicamente verificada.

### 12.9 Comprobación previa de duplicados — ejemplo

```http
POST /v1/contributions/check-duplicates HTTP/1.1
Content-Type: application/json
Idempotency-Key: demo-check-001
Cookie: <SESION_AUTENTICADA>

{
  "name": "Pharmacie Démo",
  "type": "business",
  "territory_id": "<TERRITORY_UUID>",
  "selected_point": {
    "latitude": 18.54,
    "longitude": -72.30
  }
}
```

**Respuesta de ejemplo:**

```json
{
  "success": true,
  "data": {
    "decision": "manual_review_recommended",
    "candidates": [
      {
        "code": "HT-NXV-000001",
        "distance_m": 22.4,
        "similarity_score": 0.91,
        "reasons": ["similar_name", "nearby", "same_category"]
      }
    ]
  },
  "request_id": "req_demo_002"
}
```

La operación de comprobación no reserva un lugar ni publica nada; el backend comprueba duplicados nuevamente al procesar la contribución.

### 12.10 Creación de una contribución presencial — ejemplo

```http
POST /v1/contributions HTTP/1.1
Content-Type: application/json
Idempotency-Key: example-new-place-001
Cookie: <SESION_AUTENTICADA>

{
  "mode": "on_site",
  "type": "business",
  "name": "Commerce Démo",
  "territory_id": "<TERRITORY_UUID>",
  "address": {
    "neighborhood": "Sector de demostración",
    "street": null,
    "house_number": null,
    "reference": "Frente a un punto de referencia ficticio"
  },
  "selected_point": {
    "latitude": 18.54,
    "longitude": -72.30
  },
  "gps_observation": {
    "latitude": 18.54002,
    "longitude": -72.30001,
    "accuracy_m": 18.5,
    "captured_at": "2026-11-14T20:00:00Z"
  },
  "duplicate_resolution": {
    "choice": "distinct_place",
    "justification": "Local separado con entrada propia"
  },
  "source_declaration_accepted": true
}
```

```json
{
  "success": true,
  "data": {
    "contribution_id": "<CONTRIBUTION_UUID>",
    "status": "submitted",
    "eligible_for_automatic_payment": false,
    "message": "Propuesta recibida, pendiente de verificación"
  },
  "request_id": "req_demo_003"
}
```

El servidor **no acepta** `verified: true`, `confidence_score`, `reviewer_id`, `reward_amount` ni `location_code` como campos editables del cliente. Son propiedades calculadas o asignadas por procesos privilegiados.

### 12.11 Errores normalizados

```json
{
  "success": false,
  "error": {
    "code": "DUPLICATE_REVIEW_REQUIRED",
    "message": "Se requiere revisar ubicaciones similares",
    "details": {
      "candidate_count": 2
    }
  },
  "request_id": "req_demo_004"
}
```

| HTTP | Código interno sugerido | Causa |
| --- | --- | --- |
| 400 | `INVALID_QUERY` | Parámetros inválidos |
| 401 | `UNAUTHENTICATED` | Sesión o token ausente/inválido |
| 403 | `FORBIDDEN` | Permiso insuficiente |
| 404 | `LOCATION_NOT_FOUND` | No existe o no es visible; no confirmar existencia privada |
| 409 | `DUPLICATE_REVIEW_REQUIRED` | Alta en conflicto o duplicado probable |
| 409 | `VERSION_CONFLICT` | Edición con versión obsoleta |
| 422 | `VALIDATION_ERROR` | Reglas de datos incumplidas |
| 422 | `GPS_REQUIRED_FOR_ON_SITE` | Aporte presencial sin observación permitida/útil |
| 429 | `RATE_LIMITED` | Límite alcanzado |
| 500 | `INTERNAL_ERROR` | Error inesperado sin información sensible |
| 503 | `SERVICE_UNAVAILABLE` | Dependencia temporalmente fuera de servicio |

### 12.12 Contrato publicado

Generar `openapi.json` y UI interactiva con esquemas tipados de `Location`, `Contribution`, `Territory`, `DuplicateCandidate`, `ApiError`, `Pagination`, `Coordinates` y `VerificationStatus`. Mantener ejemplos reales de *forma* pero falsos en *contenido*. Publicar pruebas de contrato para detectar rupturas de compatibilidad.

---

## 13. Modelo de datos propuesto

### 13.1 Tecnología de almacenamiento

**PostgreSQL + PostGIS** como fuente de verdad; geometrías WGS84. Utilizar `geography(Point,4326)` para distancias en metros o `geometry(Point,4326)` con conversiones explícitas según uso; índices espaciales `GiST`. `pg_trgm` para similitud de texto. No almacenar datos geográficos únicamente como strings.

### 13.2 Entidades fundamentales

| Tabla | Campos principales (resumen) | Observaciones |
| --- | --- | --- |
| `users` | `id`, `email`, `password_hash`, `display_name`, `phone_encrypted`, `email_verified_at`, `status`, timestamps | Correo único normalizado, sin contraseñas planas |
| `roles` / `user_roles` | `id`, `code`, `user_id`, `role_id` | Roles explícitos, asignación auditada |
| `user_sessions` | `id`, `user_id`, `session_hash`, `expires_at`, `revoked_at` | Sesiones revocables |
| `territories` | `id`, `parent_id`, `country_code`, `level`, `name`, `pcode`, `boundary`, `source_version`, `active` | Árbol territorial versionado |
| `territory_aliases` | `territory_id`, `language`, `alias`, `normalized_alias` | Variantes kreyòl/francés y locales |
| `locations` | `id`, `public_code`, `parent_location_id`, `access_point_id`, `name`, `normalized_name`, `type`, `point`, `territory_id`, `public_visibility`, `status`, `confidence_score`, `last_verified_at`, timestamps | Registro canónico; consulta pública solo si autorizado |
| `location_addresses` | `location_id`, `neighborhood`, `street`, `house_number`, `unit_label`, `landmark`, `access_notes`, `language` | Dirección flexible y versionable |
| `location_aliases` | `id`, `location_id`, `alias`, `language`, `normalized_alias` | Búsqueda y variantes |
| `location_versions` | `id`, `location_id`, `version`, `snapshot`, `changed_by`, `changed_at`, `reason` | Historial de campos publicados |
| `public_code_redirects` | `old_code`, `canonical_location_id`, `reason`, timestamps | Fusiones sin romper referencias |
| `contributions` | `id`, `author_user_id`, `target_location_id?`, `mode`, `type`, `proposed_payload`, `selected_point`, `status`, `duplicate_check_state`, timestamps | Propuestas autenticadas, independientes del registro canónico |
| `public_suggestions` | `id`, `payload_sanitized`, `status`, `created_at`, `abuse_review_status` | Sugerencias anónimas limitadas y no remuneradas, sin GPS residencial ni publicación directa |
| `gps_observations` | `id`, `contribution_id`, `point`, `accuracy_m`, `captured_at_client`, `received_at_server`, `source`, `retention_until` | Sensible, acceso restringido y retención mínima |
| `duplicate_candidates` | `id`, `contribution_id`, `location_id`, `score`, `reasons`, `resolution` | Evidencia de análisis |
| `reviews` | `id`, `contribution_id`, `reviewer_user_id`, `decision`, `reason`, `reviewed_at` | Conflictos de interés y auditoría |
| `verification_evidence` | `id`, `contribution_id`, `type`, `storage_key`, `visibility`, `moderation_status` | Evidencias privadas por defecto |
| `location_reports` | `id`, `location_id`, `reporter_id?`, `category`, `description`, `status`, timestamps | Reportar errores y fugas de privacidad |
| `audit_events` | `id`, `actor_id?`, `action`, `subject_type`, `subject_id`, `metadata_sanitized`, `created_at` | Registro append-only protegido |
| `developer_apps` | `id`, `owner_id`, `name`, `environment`, `plan_id`, `status` | Proyecto consumidor |
| `api_keys` | `id`, `app_id`, `prefix`, `secret_hash`, `scopes`, `expires_at`, `revoked_at` | Secretos nunca persistidos en claro |
| `api_usage_daily` | `app_id`, `day`, `endpoint_group`, `count`, `error_count` | Agregados, no GPS personal |
| `plans` / `subscriptions` | `id`, `limits`, `billing_status`, `owner_id`, timestamps | Activar al iniciar fase comercial |
| `reward_campaigns` | `id`, `status`, `budget_minor`, `currency`, `rules`, `start_at`, `end_at` | Reglas versionadas y financiadas |
| `reward_ledger` | `id`, `user_id`, `contribution_id`, `campaign_id`, `amount_minor`, `currency`, `status`, timestamps | Inmutable o compensación; no saldos mágicos |
| `payouts` | `id`, `user_id`, `provider_reference`, `amount_minor`, `status`, timestamps | Conciliación de pagos |
| `privacy_consents` | `id`, `subject_user_id`, `location_id?`, `purpose`, `scope`, `granted_at`, `revoked_at` | Consentimiento versionado |
| `private_share_tokens` | `id`, `location_id`, `token_hash`, `scope`, `expires_at`, `revoked_at`, `uses_remaining` | Fase posterior; no indexación pública |
| `import_batches` | `id`, `source_name`, `source_url`, `license`, `version`, `checksum`, `imported_at` | Procedencia de capas y catálogo |

### 13.3 Reglas del esquema

- `locations.id` UUID como PK; `locations.public_code` único para registros públicos; generar dentro de transacción.
- `users.email` único tras normalización; claves de sesión/API solo hashes.
- `locations.point` con índice GiST; `territories.boundary` GiST cuando existan polígonos.
- Índices sobre `territory_id`, `status`, `public_visibility`, `type`, `normalized_name`, alias, `last_verified_at`.
- `confidence_score` entre `0` y `1`, `accuracy_m > 0` y finita.
- Restricciones de integridad: evitar referencias cíclicas padre-hijo; FK, `ON DELETE` explícito y migraciones reversibles.
- `location_versions` y `reviews` nunca desaparecen silenciosamente; aplicar retención y anonimización cuando corresponda.
- Modelar `source_license`, `source_name` y su procedencia cuando un registro derive de un conjunto externo.
- `public_visibility` no significa que un usuario cualquiera pueda cambiarlo; publicación y exposición dependen del tipo y autorización.
- No almacenar domicilios privados en el mismo índice público de búsqueda, ni exponer sus coordenadas en vistas/materializaciones públicas.
- Considerar tablas o esquemas separados para datos residenciales y evidencias sensibles, con cifrado en reposo y RBAC estricto.

### 13.4 Consulta espacial de referencia

```sql
-- Ejemplo conceptual, requiere los nombres finales de tabla y columnas.
SELECT l.id, l.public_code, l.name,
       ST_Distance(
         l.point,
         ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography
       ) AS distance_m
FROM locations AS l
WHERE l.status = 'active'
  AND l.public_visibility = 'public'
  AND ST_DWithin(
    l.point,
    ST_SetSRID(ST_MakePoint(:lon, :lat), 4326)::geography,
    :radius_m
  )
ORDER BY distance_m ASC
LIMIT :limit;
```

La implementación real utilizará consultas parametrizadas y políticas de acceso. Usar `ST_DWithin` para filtrar por radio (en metros con `geography`) permite aprovechar índices espaciales apropiados.

### 13.5 Ciclo de escritura

`submission -> validation -> duplicate candidates -> moderation -> canonical upsert/merge -> audit -> public read model/cache invalidation`.

Mantener una transacción consistente al crear/actualizar la entidad canónica; las tareas lentas (fotos, notificaciones, recalcular índices) pueden ejecutarse de manera asíncrona e idempotente. Ninguna falla parcial puede hacer aparecer registros no aprobados en lecturas públicas.

---

## 14. Arquitectura técnica de referencia

### 14.1 Stack recomendado para iniciar

| Capa | Tecnología propuesta | Motivo |
| --- | --- | --- |
| Frontend | Next.js + React + TypeScript | Web responsiva, SEO de fichas públicas, formularios, internacionalización |
| UI | Tailwind CSS + componentes accesibles | Estilo consistente, rapidez y accesibilidad |
| Mapas | MapLibre GL JS + proveedor compatible de mapas/teselas | Visualización, marcadores y capas con control de licencia |
| Backend/API | Python + FastAPI + Pydantic | REST tipado y OpenAPI automático |
| Persistencia | PostgreSQL + PostGIS | Geometría, distancias, integridad y SQL transaccional |
| ORM/migraciones | SQLAlchemy 2 + GeoAlchemy2 + Alembic | Esquema y cambios reproducibles |
| Búsqueda | PostgreSQL `pg_trgm`, índices de texto; ampliar si fuera necesario | Resolver primero necesidades reales sin complejidad prematura |
| Caché/quotas | Redis | Limitar consumo, caché de lectura y colas sencillas |
| Procesos diferidos | Worker Python con cola | Moderación de archivos, notificaciones, importaciones |
| Archivos | Almacenamiento privado compatible S3 | Evidencias/fotos con URLs firmadas y permisos |
| Correo | Proveedor transaccional | Verificación y recuperación de cuenta |
| Logs/errores | Logs estructurados + métricas y trazas | Diagnóstico operativo |
| Infraestructura local | Docker Compose | Reproducibilidad |
| Entrega | CI/CD con staging y producción | Pruebas, migraciones y despliegues controlados |

**Nota:** las versiones exactas se fijarán a releases estables y compatibles en un archivo de dependencias al comenzar. No elegir tecnologías duplicadas sin justificación; preferir una única implementación del backend y una única fuente de verdad.

### 14.2 Componentes

```mermaid
flowchart TB
    U[Ciudadanos y colaboradores] --> FE[Web / PWA Next.js]
    DEV[Desarrolladores y empresas] --> API[FastAPI v1]
    FE --> API
    API --> AUTH[Autenticación, RBAC y privacidad]
    API --> GEO[Ubicaciones y búsqueda espacial]
    API --> CONTRIB[Aportes y duplicados]
    API --> MOD[Moderación y auditoría]
    API --> DEVPORTAL[Gestión de apps y cuotas]
    GEO --> PG[(PostgreSQL + PostGIS)]
    CONTRIB --> PG
    MOD --> PG
    AUTH --> PG
    DEVPORTAL --> PG
    API --> REDIS[(Redis)]
    CONTRIB --> Q[Cola de tareas]
    Q --> WORKER[Worker asíncrono]
    WORKER --> PG
    WORKER --> S3[(Evidencia y fotos privadas)]
    FE --> TILES[Proveedor de mapas con licencia]
```

### 14.3 Módulos backend

- `identity`: usuarios, sesiones, permisos, consentimiento.
- `territories`: catálogo, alias, jerarquía y límites.
- `locations`: entidad canónica, búsqueda, fichas y versiones.
- `contributions`: propuesta, validación y evidencia GPS.
- `deduplication`: candidatos, similitud, explicación y resolución.
- `moderation`: bandeja, decisiones, reportes y control de publicación.
- `developer`: apps, claves, límites y consumo.
- `rewards`: campañas y ledger, **desactivado inicialmente para dinero real**.
- `privacy`: visibilidad, derechos del titular y compartición autorizada.
- `audit`: eventos inmutables, trazabilidad.
- `integrations`: imports, correo, almacenamiento y pagos futuros.

### 14.4 Estructura sugerida del repositorio

```text
Haiti-Tracking-by-Nexovax/
├── HaitiTrackingbyNexovax.md       # Este documento maestro
├── README.md                       # Inicio rápido y requisitos locales
├── CHANGELOG.md
├── docs/
│   ├── architecture/
│   │   └── decisions/              # ADR-0001, ADR-0002, etc.
│   ├── api/                        # OpenAPI, ejemplos y guías
│   ├── privacy/                    # Consentimientos y políticas operativas
│   ├── product/                    # Flujos, diseños, criterios y roadmap
│   └── operations/                 # Runbooks, backups, incidentes
├── apps/
│   └── web/                        # Next.js
├── services/
│   └── api/                        # FastAPI
│       ├── app/
│       │   ├── core/
│       │   ├── modules/
│       │   └── tests/
│       ├── migrations/             # Alembic
│       └── pyproject.toml
├── packages/
│   └── contracts/                  # Tipos/SDK generados desde OpenAPI
├── infra/
│   ├── docker/
│   ├── compose.yaml
│   └── deployment/
├── scripts/
│   └── seed_territories/
├── .env.example                     # Solo variables ficticias
└── .github/workflows/              # CI/CD
```

### 14.5 Configuración y secretos

```dotenv
# Plantilla ilustrativa: NO colocar valores reales en el repositorio.
APP_ENV=development
WEB_BASE_URL=http://localhost:3000
API_BASE_URL=http://localhost:8000
DATABASE_URL=postgresql+psycopg://user:password@localhost:5432/haiti_tracking
REDIS_URL=redis://localhost:6379/0
SESSION_SECRET=CHANGE_ME_LOCAL_ONLY
API_KEY_PEPPER=CHANGE_ME_LOCAL_ONLY
EMAIL_PROVIDER_API_KEY=
OBJECT_STORAGE_ENDPOINT=
OBJECT_STORAGE_BUCKET=
OBJECT_STORAGE_ACCESS_KEY=
OBJECT_STORAGE_SECRET_KEY=
MAP_TILES_URL=
MAP_TILES_ATTRIBUTION=
REWARDS_CASH_ENABLED=false
PRIVATE_ADDRESS_SHARING_ENABLED=false
```

Variables reales se almacenan en un gestor de secretos; la plantilla `env.example` y Docker Compose solo sirven de guía local. Configurar CORS con orígenes permitidos específicos; no usar comodines con credenciales.

---

## 15. Seguridad, privacidad y protección de personas

### 15.1 Matriz de visibilidad

| Recurso | Visitante | API B2B | Autor/titular | Moderación autorizada |
| --- | --- | --- | --- | --- |
| Lugar público aprobado | Sí | Sí | Sí | Sí |
| Comercio aprobado y publicado | Sí | Sí | Sí | Sí |
| Borrador de contribución | No | No | Su autor | Solo si permiso y necesidad |
| Propuesta bajo revisión | No | No | Su autor | Sí |
| Observación GPS del aportante | No | No | Acceso restringido de su expediente | Solo necesidad justificada |
| Evidencia fotográfica pendiente | No | No | Autor según permiso | Sí, restringida |
| Dirección residencial privada exacta | No | No | Titular autorizado | Acceso excepcional auditado |
| Enlace residencial temporal | No indexado | No por defecto | Titular gestiona | Sólo soporte justificado |
| Datos de identidad/pagos | No | No | Persona según derechos | Personal financiero restringido |

### 15.2 Datos personales y riesgos

- Obtener consentimiento claro para usar GPS en cada flujo; permitir negarse sin bloquear la consulta general.
- Recoger únicamente la posición necesaria para registrar el punto, no historial de recorridos ni localización continua.
- Cifrar en tránsito con HTTPS/TLS y en reposo datos sensibles y backups; aplicar permisos por componente.
- Retención propuesta de observaciones GPS brutas: corta y configurable (por ejemplo, 30 días desde decisión firme, salvo necesidad documentada de investigación); validar política final con responsables jurídicos y operativos.
- Eliminar metadatos EXIF de fotografías antes de cualquier publicación y retirar imágenes con caras, matrículas u otra información sensible cuando corresponda.
- Moderación proactiva de fichas que revelen residencias, refugios, instalaciones vulnerables o accesos privados; clasificación según contexto y riesgo.
- Mantener canales de corrección, supresión, oposición/retirada de publicación y apelación conforme al marco legal aplicable.
- No inferir ciudadanía, domicilio habitual, religión, pertenencia política ni otras características sensibles por geolocalización.
- No incluir coordenadas precisas ni tokens de invitación en analytics, URL públicas, logs de error o herramientas de atención.
- Reducir la precisión de métricas agregadas que podrían identificar hogares individuales.

### 15.3 Riesgos técnicos a controlar

- Inyección SQL: consultas parametrizadas y validación de filtros.
- XSS/HTML: escapado en renderizado, sanitización de textos y CSP.
- CSRF: protección en operaciones de sesiones con cookies.
- SSRF: bloquear URLs de recursos no confiables y metadatos de cloud.
- IDOR/BOLA: comprobar propiedad y permisos de cada objeto.
- Abuso de API: rate limits, cuotas, detección de extracción masiva, revocación.
- Filtración por geocodificación inversa: aplicar filtros de privacidad **antes** del cálculo de resultados mostrables.
- Enumeración de residencias: no indexar, no permitir `GET` por código privado estable ni respuestas diferenciadas que revelen existencia.
- Ataques de archivos: limitar tamaño/tipo, inspección de contenido, escaneo, metadatos y URLs firmadas.
- Acceso administrativo: MFA, mínimo privilegio, sesiones cortas, auditoría y revisión de cambios.
- Fraude de GPS: no atribuir prueba criptográfica de presencia a `navigator.geolocation`; usar evidencias múltiples y revisión.
- Abuso financiero: segregación de funciones, antifraude, conciliación y reversos.

### 15.4 Modelo residencial privado (fase posterior)

Separar claramente **registrar una vivienda para su titular** de **publicar un lugar para cualquier persona**.

1. El titular verifica su autorización por un proceso definido legal y operativamente.
2. La coordenada exacta se almacena de forma protegida y no entra al índice de búsqueda pública.
3. El titular crea una autorización temporal con alcance, expiración, posible límite de usos y revocación.
4. El token se entrega al destinatario autorizado; preferir canjearlo por `POST` para reducir exposición en historial de navegación/referrers.
5. La API devuelve solo la información estrictamente concedida.
6. Cualquier incidente permite revocación y auditoría inmediata.

**No implementar un mapa público con pines de viviendas por decisión unilateral de un colaborador.**

---

## 16. Portal de desarrolladores y monetización B2B

### 16.1 Funcionalidades de portal

- Crear cuenta de desarrollador/organización.
- Crear aplicación `test` o `live` y asignar permisos.
- Generar, rotar y revocar claves; secreto mostrado una única vez.
- Leer guías `curl`, JavaScript, Python y ejemplos de respuestas.
- Explorar documentación Swagger/OpenAPI.
- Ver solicitudes por día/mes, errores, uso aproximado de cuota y plan.
- Configurar alertas de consumo y límites antes de agotarse.
- Gestionar facturación/suscripción cuando se active el modelo comercial.
- Soporte para incidentes y cambios de versión.

### 16.2 Planes propuestos

| Plan | Perfil | Reglas |
| --- | --- | --- |
| Free | Experimentación/estudiantes | Cuota pequeña, documentación y acceso de prueba |
| Pro | Apps de delivery y comercios | Cuota superior, consultas avanzadas, métricas, soporte |
| Enterprise | Logística y plataformas grandes | Límites y contratos negociados, soporte y disponibilidad acordada |

Los precios no están fijados. Definir costo por petición, almacenamiento, mapas, soporte y verificaciones antes de poner tarifas en producción. No comprometer SLA cuantitativo antes de tener medición y capacidad operativa.

### 16.3 Facturación y uso

- Medición por `app_id`, ruta/grupo, estado, instante y período de facturación.
- Cuotas configurables por plan, con protección contra consumo anómalo y sobrefacturación.
- Evitar métricas que expongan coordenadas exactas de la consulta de una persona.
- Permitir entornos de sandbox separados y claves de pruebas sin cargos.
- Contabilidad y facturas alineadas con obligaciones legales aplicables, tras revisión profesional.

---

## 17. Datos base, fuentes y licencias

### 17.1 Catálogo territorial

Adoptar una fuente geográfica versionada para límites administrativos y conservar su identificación original. Los recuentos publicados de comunas y secciones varían entre algunas referencias, por lo que **no deben congelarse en el código**. Documentar la decisión sobre el catálogo inicial, su fecha y mecanismo de actualización.

Proceso esperado:

1. Seleccionar fuente primaria y verificar términos de uso/atribución.
2. Descargar en lote de importación con checksum y metadatos, no editar manualmente datos crudos.
3. Validar geometrías, IDs, nombres, jerarquía, relaciones padre-hijo y duplicados.
4. Importar usando migraciones/seed reproducible; publicar versión de catálogo.
5. Añadir alias documentados de nombres regionales sin sobrescribir el nombre original.
6. Comparar revisiones nuevas, mantener redirecciones de IDs si corresponde y registrar cambios.

### 17.2 Cartografía base

Se puede usar tecnología abierta basada en OpenStreetMap, **pero la licencia de datos ODbL no equivale a autorización ilimitada para consumir los servidores de teselas de la fundación**. Elegir proveedor de mapas adecuado, contrato o infraestructura propia; exhibir atribución y cumplir las políticas respectivas. No copiar lugares de servicios propietarios de terceros sin licencia compatible. Mantener registro de fuente por capa/importación y revisar obligaciones de bases derivadas antes de distribuir la API comercial.

### 17.3 Datos comunitarios

La contribución original debe incluir términos de licencia y uso claros aceptados por el autor, con límite de publicación de información de terceros. Un dato aportado por una persona no se vuelve publicable por haber sido enviado: la plataforma revisa naturaleza, procedencia, autorización y riesgo.

---

## 18. Operaciones, desempeño y calidad

### 18.1 Objetivos no funcionales iniciales

- Diseño mobile-first y tolerancia a redes lentas.
- Consultas geográficas eficientes con índices GiST y límites de radio/resultado.
- Caché de datos públicos no sensibles con invalidación al editar, fusionar u ocultar.
- Paginación en endpoints y paneles administrativos.
- Procesamiento de fotografías y notificaciones fuera de la respuesta HTTP principal.
- Monitoreo de latencia p50/p95, errores 4xx/5xx, conexiones, uso de caché y cola.
- Trazabilidad de operaciones con `request_id`; filtrado de secretos y GPS en logs.
- Backups cifrados con restauración probada periódicamente.
- Despliegue de staging antes de producción, rollback documentado y migraciones controladas.
- Alertas de fallas, abuso y cambios críticos de visibilidad.

### 18.2 Metas de rendimiento (orientativas para validar en piloto)

- `GET /locations/{code}` p95 deseado bajo carga normal: **< 500 ms** en backend sin contar latencia móvil extrema.
- Búsqueda pública p95 deseado: **< 1000 ms** para catálogo inicial y filtros habituales.
- Disponibilidad/SLA comercial: **por definir tras instrumentación**.
- Calidad de duplicados: medir precisión y recall sobre pares etiquetados; calibrar umbrales con datos reales, no asumir exactitud del algoritmo.

Las cifras son metas de diseño sujetas a pruebas, **no métricas actuales**.

### 18.3 Mantenimiento y documentación

- OpenAPI actualizado desde el código y revisado en PR.
- ADR para decisiones tecnológicas significativas.
- Manual de operaciones, backups, restauración, rotación de secretos y respuesta a incidentes.
- Documentación de datos, procedencia, licencia, esquema y políticas de retención.
- Registro de cambios de contratos API y del catálogo territorial.
- Pruebas de accesibilidad y revisión editorial de traducciones.

---

## 19. Estrategia de pruebas

### 19.1 Pruebas unitarias

- Normalización de nombres, abreviaturas y variantes.
- Validación de coordenadas, precisión y rangos.
- Reglas de roles, estados y visibilidad.
- Cálculo y explicación de similitud duplicada.
- Reglas de campañas/recompensas (sin dinero real en pruebas).
- Expiración/revocación de claves API y enlaces privados.

### 19.2 Pruebas de integración

- PostGIS: búsqueda espacial y orden por distancia en metros.
- Migraciones `upgrade` y `downgrade` bajo una estrategia de base temporal.
- Creación de propuestas idempotente con `Idempotency-Key`.
- Revisión y publicación transaccional.
- Fusión de registros manteniendo código previo como alias.
- API key válida/inválida/revocada con cuotas y `429`.
- Ausencia de ubicaciones privadas en todas las rutas públicas.
- Retirada/ocultación de registro e invalidación de caché.

### 19.3 Pruebas end-to-end (web)

- Visitante busca una ubicación sin autorización GPS.
- Usuario se registra y verifica correo.
- Aporte presencial solicita GPS después de acción expresa.
- Usuario deniega GPS: puede seguir consultando y guardar borrador, no enviar como presencia verificada.
- Usuario confirma pin y completa formulario con calle/número inexistentes.
- El sistema muestra candidatos similares y permite actualizar uno existente.
- Moderador aprueba, rechaza, solicita cambios y fusiona con razón.
- Una ubicación pública aprobada aparece en mapa y API; una privada no.
- Desarrollador crea clave, consulta API, observa consumo y revoca el secreto.

### 19.4 Pruebas de seguridad y abuso

- IDOR/BOLA en propuestas, evidencias, claves y pagos.
- Enumeración de códigos, límites de búsqueda y protección del catálogo privado.
- Acceso a fotos sin autorización, URLs firmadas expiradas.
- CSRF, XSS, SQL injection, SSRF, subida de archivos y fuga de secretos.
- Spoofing o discrepancia de GPS; lectura inexacta.
- Repetición de solicitudes, carreras en aprobación y duplicados simultáneos.
- Roles que intentan autoaprobar su aporte o pagarse a sí mismos.

---

## 20. Criterios de aceptación del MVP (Definition of Done)

Se considerará listo para piloto cuando se cumpla **todo** lo siguiente:

1. El repositorio inicia con instrucciones reproducibles y `env.example` sin secretos reales.
2. La base PostgreSQL/PostGIS se crea y migra de forma automatizada.
3. Existe catálogo territorial versionado con fuente y alias.
4. El usuario puede registrarse, verificar su correo, iniciar sesión y cerrarla.
5. Las páginas públicas permiten buscar sin exigir cuenta ni GPS, y enviar una sugerencia no remunerada con controles antiabuso.
6. El formulario captura GPS con permiso explícito, guarda precisión y permite seleccionar acceso real en el mapa.
7. Sin GPS no se puede etiquetar una contribución como presencial verificada; el sistema ofrece flujo alternativo no elegible para recompensa.
8. El formulario admite zonas sin calle o número formal.
9. Antes de publicar se buscan posibles duplicados y se documenta la resolución.
10. Una propuesta pasa por moderación con estado y motivo auditado.
11. Las ubicaciones públicas aprobadas reciben código estable y aparecen en mapa/API.
12. El flujo de fusión conserva el historial y las referencias de código anteriores.
13. Ninguna residencia privada ni dato GPS bruto del colaborador se devuelve en búsquedas/consultas públicas.
14. Se pueden reportar errores y retirar datos publicados por razones de privacidad.
15. `GET /locations/search`, `GET /locations/{code}`, `GET /locations/nearby` y `GET /territories` funcionan, están documentados y cuentan con validación.
16. API keys se generan y revocan con control de acceso y rate limit.
17. El entorno distingue desarrollo, pruebas y producción.
18. Los casos críticos de pruebas unitarias, integración, e2e y privacidad pasan en CI.
19. La web es utilizable en móvil y se ha probado en conexión lenta.
20. Las pantallas críticas están disponibles al menos en kreyòl y francés.
21. Logs y métricas omiten secretos y coordenadas privadas; existe procedimiento de backup y restauración.
22. No se presentan recompensas, contadores o ingresos ficticios como hechos.
23. No hay pagos reales habilitados en MVP salvo revisión comercial, financiera y legal por separado.
24. El equipo valida un piloto limitado en una comuna/área antes de expansión nacional.

### 20.1 Escenarios de aceptación concretos

**Caso A — búsqueda anónima:** abrir `/mapa` en móvil; sin permiso GPS ni login, buscar un establecimiento aprobado. Resultado esperado: ficha pública y código; no aparece solicitud de GPS innecesaria.

**Caso B — señal imprecisa:** el colaborador tiene una estimación GPS de 150 m. Resultado: la app explica incertidumbre, no aprueba automáticamente como evidencia exacta y permite reintento o revisión.

**Caso C — mismo edificio, dos negocios:** los puntos están a 6 m. Resultado: el motor los marca como posibles coincidencias, pero admite dos negocios legítimos si nombres/unidades/accesos difieren y revisión los valida.

**Caso D — dirección privada:** un tercero solicita por API una residencia almacenada de forma protegida. Resultado: no obtiene detalles ni confirmación de existencia; los logs tampoco exponen el punto.

**Caso E — corrección de ubicación:** tras aprobar un cambio, el código original continúa funcionando y apunta a la ficha actualizada, con historial conservado.

**Caso F — carrera en duplicados:** dos usuarios envían el mismo negocio casi simultáneamente. Resultado: se genera una revisión/consolidación consistente y no dos ubicaciones activas idénticas por fallo de concurrencia.

**Caso G — token revocado:** se usa una API key revocada. Resultado: `401`, sin acceso, y evento de seguridad según política.

---

## 21. Backlog recomendado con dependencias

| Prioridad | Épica / entrega | Depende de | Criterio de salida |
| --- | --- | --- | --- |
| P0 | Repositorio, CI, variables y entornos | Ninguna | Proyecto arranca reproduciblemente |
| P0 | Datos territoriales y PostGIS | Base | Seed validado y consultas espaciales |
| P0 | Usuarios, roles, sesiones y correo | Base | Acceso/registro verificados |
| P0 | Mapa y búsqueda pública | Territorios, API read | Fichas públicas consultables |
| P0 | Formulario GPS y propuesta | Auth, mapa, territorio | Aporte enviado y auditable |
| P0 | Dedupe v1 | PostGIS, contribución | Candidatos explicables y flujo de revisión |
| P0 | Moderación, publicación y códigos | Dedupe, auth | Aprobación sin filtraciones privadas |
| P0 | API v1 + documentación | Ubicaciones aprobadas | Contratos y pruebas de API |
| P0 | Privacidad, reportes y seguridad | Transversal | Casos críticos aprobados |
| P1 | Versionado completo y reputación | MVP | Correcciones y calidad comunitaria |
| P1 | Fotos y revisión mejorada | Moderación, almacenamiento | Archivos seguros y controlados |
| P1 | Portal de desarrolladores | API y auth | Apps, claves, cuotas, consumo |
| P2 | Campañas y ledger de recompensas | Calidad, antifraude, financiamiento | Piloto sin pagos automáticos |
| P2 | Planes comerciales y cobro | Portal y legal | Facturación y límites consistentes |
| P3 | Compartición residencial privada | Privacidad, verificación de titular | Tokens revocables y no indexados |
| P3 | PWA offline y mejoras nacionales | MVP probado | Cobertura y sincronización robustas |

### 21.1 Entregables por fase

Cada fase produce: código, migraciones, pruebas automatizadas, OpenAPI (si hay API nueva), pantallas revisadas, documentación de decisiones y demo en staging. Nada se considera implementado solo porque esté descrito o maquetado.

---

## 22. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
| --- | --- | --- |
| Baja precisión GPS | Ubicación incorrecta | Mostrar error estimado, reintentos, confirmación pin, revisión |
| Spoofing de presencia | Incentivos fraudulentos | Evidencias múltiples, límites, auditoría, verificación independiente |
| Publicación de residencias privadas | Daño a personas y confianza | Modelo separado, privacidad por defecto, reporte y retirada urgente |
| Duplicados legítimos confundidos | Pérdida de lugares reales | Tipos y unidades, revisión, puntajes explicables, no fusión ciega |
| Inconsistencia territorial | Búsquedas fallidas | Catálogo versionado, alias y trazabilidad de fuentes |
| Limitaciones de redes móviles | Abandono de formularios | Mobile-first, borradores, compresión y reintento |
| Costos de mapas/API | Modelo B2B no rentable | Cuotas, caché, proveedor adecuado y seguimiento de costos |
| Conflictos de licencias | Restricciones comerciales | Registro de fuentes y revisión de contratos/licencias |
| Pagos antes de verificación | Fraude y riesgo financiero | Fases, ledger, presupuesto cerrado, aprobación dual |
| API scraping masivo | Abuso y fuga indirecta | Autorización, cuotas, detección, mínimos de respuesta |
| Datos desactualizados | Usuarios no encuentran sitios | Reportes, revalidación, fecha visible y campañas de actualización |
| Abuso interno | Exposición de registros | MFA, segregación de roles, auditoría y revisiones periódicas |

---

## 23. Decisiones abiertas que requieren validación de negocio

Estas preguntas **no bloquean** construir el esqueleto y el MVP público seguro. Se registrarán como decisiones explícitas antes de activar módulos afectados.

1. **Marca y dominios:** verificar disponibilidad y registro de dominios; `haititracking.com`, `api.haititracking.com` y `developers.haititracking.com` son ejemplos, no activos confirmados.
2. **Zona piloto:** seleccionar comuna/barrio con capacidad real de verificación local.
3. **Fuente administrativa primaria:** elegir dataset, licencia, fecha y responsable de actualización; mantener alias entre fuentes.
4. **Proveedor de mapas:** elegir tiles, costo, atribución, almacenamiento y política de uso comercial.
5. **Proveedor de hosting:** criterios de disponibilidad, soberanía de datos, presupuesto y respaldo.
6. **Idiomas del MVP:** mantener como base kreyòl y francés; decidir si español aparece también en interfaz pública.
7. **Gobernanza comunitaria:** requisitos de verificador, resolución de disputas y umbrales de reputación.
8. **Residencias privadas:** procedimiento para demostrar titularidad/autorización y alcance permitido; no habilitar publicación por defecto.
9. **Recompensas:** presupuesto, validación de identidad, impuestos, proveedor de pago y campañas. Hasta resolverlo, deshabilitadas para dinero real.
10. **Planes API:** volumen gratuito, límites, precios y términos de uso.
11. **Política de retención:** tiempos definitivos para observaciones GPS, imágenes, auditoría y pagos, con revisión legal y operativa.
12. **Nivel de verificación:** calibrar radios, score y criterios con datos del piloto, no fijarlos como verdades universales.
13. **Licencias de datos comunitarios:** documento público de permisos, atribución y uso en API.

### 23.1 Valores por defecto mientras se decide

- Enfoque inicial: establecimientos y puntos públicos; **sin residencias privadas publicadas**.
- Consulta pública gratuita desde la web; API comercial mediante claves y cuotas.
- GPS con permiso explícito solo durante contribución presencial.
- Moderación humana de todos los nuevos registros en el piloto.
- Recompensas monetarias deshabilitadas.
- Una sola área piloto y expansión gradual.
- Rutas y ETA proporcionadas por motores de navegación externos, no por esta API en MVP.

---

## 24. Referencias técnicas y fuentes a validar

Estas referencias ayudan a implementar decisiones técnicas y verificar condiciones de uso. **No son datos cargados en el proyecto ni garantizan disponibilidad de servicios comerciales.** Registrar fecha y licencia exacta de cada dataset al importarlo.

1. **Geolocation API (MDN):** https://developer.mozilla.org/en-US/docs/Web/API/Geolocation_API — permisos explícitos, geolocalización web y HTTPS.
2. **`getCurrentPosition` (MDN):** https://developer.mozilla.org/en-US/docs/Web/API/Geolocation/getCurrentPosition — `enableHighAccuracy`, `maximumAge`, `timeout`.
3. **Precisión GPS (MDN):** https://developer.mozilla.org/en-US/docs/Web/API/GeolocationCoordinates/accuracy — exactitud estimada expresada en metros.
4. **PostGIS `ST_DWithin`:** https://postgis.net/docs/ST_DWithin.html — consultas espaciales y distancias en metros para `geography`.
5. **Licencia de OpenStreetMap:** https://www.openstreetmap.org/copyright — ODbL y atribución.
6. **Política de teselas OpenStreetMap:** https://operations.osmfoundation.org/policies/tiles/ — uso de servidores de tiles y limitaciones.
7. **OCHA, límites administrativos COD-AB:** https://knowledge.base.unocha.org/wiki/spaces/imtoolbox/pages/2557378679/Administrative%20Boundaries%20COD-AB — procedencia y revisión de límites.
8. **Gobernanza territorial de Haití (OCDE):** https://www.oecd.org/en/publications/oecd-public-governance-reviews-haiti_dfd5f806-en/full-report/multi-level-governance-in-haiti_7481a6aa.html — contexto institucional.
9. **Portal gubernamental de descentralización de Haití:** https://omrh.gouv.ht/decentralisation — niveles territoriales reconocidos.
10. **Documentación del proyecto:** el texto de idea original aportado por el propietario y las decisiones de las conversaciones sobre geolocalización, diseño de interfaz y API; no se trata de requisitos ya implementados.

---

## 25. Glosario

- **Ubicación:** entidad geográfica documentada (negocio, edificio, hito, punto de acceso, etc.).
- **Punto de acceso:** coordenada de entrada física preferible al centroide para entregas.
- **Contribución:** propuesta de creación, corrección o verificación; no es una ubicación publicada.
- **Registro canónico:** versión aprobada y referenciada por el código estable.
- **GPS observado:** lectura del dispositivo con estimación de precisión; no prueba definitiva.
- **Geocodificación:** búsqueda de candidatos geográficos a partir de texto.
- **Geocodificación inversa:** obtención de territorio/referencias a partir de coordenadas.
- **Duplicado:** dos registros que representan la **misma entidad**, no simplemente dos puntos cercanos.
- **Confianza:** valoración de calidad de ubicación, independiente de precisión del GPS.
- **Código público:** identificador `HT-NXV-...` para lugares que pueden divulgarse.
- **API key:** credencial de una aplicación consumidora, distinta de la sesión de usuario.
- **POI:** *Point of Interest*, punto de interés.
- **MVP:** producto mínimo viable que valida la utilidad central con controles reales.
- **PWA:** aplicación web progresiva; capacidad futura de mejorar uso móvil y conectividad.
- **ODbL:** licencia de base de datos de OpenStreetMap, con obligaciones específicas.
- **HTG:** código monetario de la gourde haitiana.

---

## 26. Cierre: qué se está construyendo

**Haiti Tracking by Nexovax es una infraestructura colaborativa de direcciones digitales verificables, con una interfaz pública de mapas, una comunidad que aporta datos geográficos, controles rigurosos de duplicados y privacidad, un backoffice de verificación y una API REST apta para integración empresarial.**

La prioridad inicial **no** es competir con todos los servicios de mapas ni pagar por cada pin capturado. Es crear una base de puntos útiles, correctamente identificados, comprobables, mantenibles y seguros de compartir. El éxito vendrá de la cobertura validada, la calidad de las referencias locales y la confianza de ciudadanos y desarrolladores.

**Estado al emitir este documento:** especificación inicial completa para planificación, desglose de tareas, implementación de MVP y revisión técnica. No indica que el sistema, dominios, APIs, cifras, pagos o integraciones estén ya operativos.
