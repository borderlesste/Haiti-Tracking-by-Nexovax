# Comparación visual y funcional

**final result: passed** — para revisión local del MVP funcional. No significa réplica píxel a píxel, certificación de producción o aceptación del piloto.

Fecha: 2026-11-15. Fuente visual: `Interfaz Haiti Tracking_ Mapa y Contribuciones.png`, idéntica a la referencia adjunta. Requisitos de contenido/estados: documento maestro, especialmente §6.6 (referencia orientativa), privacidad, GPS explícito y exclusión de pagos.

## Artefactos y normalización

La fuente mide **1672×941 píxeles** y reúne tres pantallas. No se implementó como una imagen de fondo ni como tres aplicaciones encogidas dentro de una página.

| Pantalla | Fuente raster | Implementación y estado | Comparación conjunta |
| --- | --- | --- | --- |
| Portada | Recorte (7,33)–(758,937), 751×904 | `docs/evidence/home-750.png`, 750×941; viewport 750×941 CSS px, DPR 1. Anónimo, ES, métricas reales cargadas, mapa público sin lugares ficticios | `docs/evidence/compare-home.png`; detalle `compare-hero-focus.png` |
| Registro | Recorte (766,30)–(1062,931), 296×901 | `registration-330-es.png`, 330×1282; viewport 330×941, DPR 1, documento 320 CSS px por scrollbar. Formulario vacío, ES | `compare-registration.png` |
| Contribución | Recorte (1073,29)–(1664,931), 591×902 | `contribution-591.png`, 591×1806; viewport 591×941, DPR 1. Cuenta QA, GPS pendiente, territorio seleccionado, foco en selector de comuna | `compare-contribution.png` |

Los recortes se hicieron solo en artefactos diagnósticos; originales intactos. Cada comparación contiene fuente e implementación juntas, a escala raster nativa, sin estirar la tipografía. El viewport CSS y la densidad originales del collage no se conocen: no se deduce una precisión de píxel que la referencia no permite. El registro original tiene 34 px menos de anchura; las alturas y los estados GPS también difieren. El foco visible de archivo y la posición de elementos fijos en una captura de página completa no pertenecen al estado neutro de la fuente.

## Hallazgos y segunda revisión

| Prioridad inicial | Evidencia | Corrección y comprobación posterior |
| --- | --- | --- |
| P2 · anatomía de contribución a ancho intermedio | La columna de calidad pasaba debajo del formulario aunque había espacio para la composición lateral de la referencia | Grid lateral conservado desde 560 px; a 591 px se ven formulario y calidad juntos. Por debajo se apilan para mantener uso móvil. Ver comparación final y `contribution-mobile.png` |
| P2 · control de fotos y densidad | `compare-contribution-before.png` mostraba un segundo botón nativo dentro del área dibujada; controles/espacios agrandaban la composición | Input nativo cubre el área sin duplicar su presentación; foco de teclado dibuja contorno visible. Se ajustaron espaciado, tamaño de campos y mapa en tablet. Comprobado `activeElement.type=file`, `outlineStyle=solid` y selección accesible conservada |
| P2 · estado de carga/errores | Durante construcción hubo fallo HMR de contexto y errores genéricos que confundían validación con conexión | Contextos estables, errores asociados, botones ocupados sin saltos, carga de catálogo antes de presentar estado listo. Recorridos de navegador y pruebas web/API registrados |
| P2 · formulario/diálogo | Foco se perdía al desaparecer el disparador tras una mutación | Diálogo nativo con título, Escape y retorno al disparador o al contenido. Revocación cancelada y moderación confirmada en navegador |

La segunda revisión abrió las comparaciones conjuntas después de estos cambios. No quedan P0/P1/P2 visuales sin tratar fuera de las adaptaciones funcionales declaradas abajo. La auditoría estática premium también pasó sin hallazgos; no se utiliza como sustituto de las capturas.

## Cinco superficies de fidelidad

- **Tipografía:** Nunito Sans variable local, jerarquía pesada de títulos y etiquetas compactas. La familia exacta del raster no está identificada; se eligió por forma/peso, no se afirma disponer de su fuente original. La portada conserva tres líneas y subrayado rojo. Registro y formularios tienen etiquetas persistentes y texto legible; se acepta más altura que el collage para áreas de interacción y mensajes reales.
- **Espaciado y disposición:** navegación blanca, hero de dos columnas a 750 px, cuatro estadísticas superpuestas y cuatro pasos, panorama inferior. Registro como tarjeta única y formulario con calidad lateral en anchos intermedios/escritorio. A 390 y 330 px se comprobó ausencia de overflow horizontal. El formulario completo requiere scroll; sus controles de consentimiento, captura y alternativa manual no están comprimidos para imitar una captura estática.
- **Colores/tokens:** azul marino/cobalto, CTA rojo, superficie azul muy clara, bordes suaves y estados verde/amarillo. Tokens en `DESIGN.md` y CSS. Se mantienen contraste de texto/foco y estados que no dependen solo del color; no se afirma una auditoría exhaustiva con lector de pantalla.
- **Imágenes/activos:** bandera raster de fuente pública, pin e iconos Phosphor coherentes, panorama generado con casas/bahía/Citadelle y exportado a WebP; no se presenta como fotografía geográfica literal. Mapa Leaflet/OSM real con atribución. Animación LottieFiles solo durante captura pendiente y oculta con movimiento reducido. Procedencia en `SOURCES.md`.
- **Contenido:** títulos, orden de campos, tarjetas de cuenta, mapa, calidad, duplicados, fotos y acciones siguen la referencia. Se corrigió «Acepto la Política de privacidad». Los textos operativos respetan el maestro; métricas, precisión, coincidencias y recompensas no se inventan para rellenar la pantalla.

## Diferencias aceptadas por los requisitos del producto

1. El collage muestra cifras, GPS 4,8 m, confianza 85 %, coincidencias y 50 HTG. La base limpia muestra cero, el GPS espera permiso, los candidatos requieren consulta y los pagos están deshabilitados. Reproducir esos valores como hechos contradiría el maestro.
2. El mapa operativo y sus etiquetas proceden de OSM, no del dibujo estilizado. La posición no se solicita al abrir páginas públicas.
3. Teléfono opcional, contraseña de 12 caracteres, calle/número opcionales, consentimiento de fuente, pin y coordenadas editables satisfacen seguridad/semántica de dirección. Añaden altura respecto de la imagen.
4. El estado positivo de GPS de la fuente no se pudo reproducir con permisos en este navegador. Se comprobó denegación y borrador; captura positiva y validación de precisión se probaron por API con datos sintéticos. Hardware real sigue pendiente.
5. La navegación móvil usa menú, los formularios se apilan a anchos estrechos y existe footer de privacidad. No se fuerza el collage de escritorio dentro de un teléfono.

## Pulido P3 y límites

El archivo de marca/fuente original y el trazo decorativo exacto permitirían una identidad aún más fiel; no impiden el uso ni se presentan como un clon exacto. La posición y el tamaño del subrayado y algunos iconos decorativos difieren ligeramente. La aprobación editorial nativa FR/HT, lectores de pantalla, zoom de sistema y teléfonos reales permanecen pendientes.

## Checklist de revisión local

- [x] Abrir fuente e implementación, comparación conjunta completa y región hero con texto/iconos legibles.
- [x] Repetir captura tras arreglar densidad/control de fotos y disposición tablet.
- [x] Verificar estados vacío, carga, error, borrador, aprobación, revocación y privacidad.
- [x] Comprobar francés/kreyòl, anchos 330/390/591/750/1440 y foco de teclado relevante.
- [x] Compilar y ejecutar pruebas web; API/PostGIS por separado, con límites en los informes.
- [ ] Certificar piloto operativo, GPS físico, entrega externa, accesibilidad asistiva y despliegue gratuito completo.


Actualización 2026-11-15: se comprobaron recibos y retiro a 390 px, persistencia de alias/sección, diálogo QR con copia/Escape/foco, resumen administrativo, edición territorial versionada y filtro de auditoría en ES/FR/HT. El auditor estático premium estricto dio cero hallazgos; no sustituye WCAG manual formal. Los campos adicionales opcionales quedan en un desplegable; la fuente del conocimiento y revisión previa responden al maestro. El envío final con GPS ficticio fue comprobado después en Chromium aislado; GPS físico y validación de campo siguen pendientes, explícitos en WEB-E2E y ACCEPTANCE.

Actualización de automatización: cinco E2E Playwright pasaron en Chromium aislado a 390 × 844, incluido el resumen antes del envío y la denegación de GPS con respuestas ficticias. No valida GPS físico, todos los escenarios del maestro ni CI remoto. Ver docs/WEB-E2E.md.
