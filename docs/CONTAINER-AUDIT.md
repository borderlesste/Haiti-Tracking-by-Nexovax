# Auditoría de paquetes OS de contenedores

Fecha: 2026-11-15. Se analizaron las imágenes locales `haiti-tracking-verify-api:latest` y `haiti-tracking-verify-web:latest`, antes y después de la actualización de paquetes/reconstrucción realizada por el responsable de integración. Evidencia detallada: `docs/container-audit.json`.

El análisis usa Trivy oficial `0.76.2`, fijado por digest `sha256:8f6bb947dbc528902e11f2f5be52f7b519f6a39d5d148f41166f2040499768fb`. La base CVE fue actualizada el `2026-11-15T01:07:39Z` y descargada a las `03:32:57Z`. Los escaneos se ejecutaron sin red, con telemetría deshabilitada, `--scanners vuln --pkg-types os --skip-db-update`. No se subieron imágenes, utilizaron cuentas de pago, modificaron servicios remotos ni intentó explotar producción. [Instalación oficial](https://trivy.dev/docs/latest/getting-started/installation/), [escaneo de imágenes](https://trivy.dev/docs/latest/target/container_image/).

## Resultado comparativo

| Imagen / ronda | Paquetes OS | CRITICAL | HIGH | MEDIUM | LOW | UNKNOWN | Coincidencias |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| API inicial · Debian 13.7 | 87 | 0 | 49 | 90 | 65 | 5 | 209 |
| API reconstruida · Debian 13.7 | 87 | 0 | 47 | 89 | 65 | 5 | 206 |
| Web inicial · Alpine 3.24.4 | 71 | 0 | 3 | 2 | 0 | 0 | 5 |
| Web reconstruida · Alpine 3.24.4 | 71 | 0 | 0 | 0 | 0 | 0 | 0 |

Los recuentos son **pares paquete/CVE**, no vulnerabilidades explotables demostradas de la aplicación. La API inicial tenía 13 CVE HIGH distintos; la reconstruida conserva 11. Algunos avisos de un paquete fuente se repiten en varios binarios. Trivy también avisó que ciertas severidades proceden de otros proveedores. El estado `fixed` del registro de un proveedor indica que existe una versión corregida; no que la imagen examinada ya la incluya.

| Imagen | ID Docker inicial | ID Docker después |
| --- | --- | --- |
| API | `e2082195db48…` | `b94e8ecbc904…` |
| Web | `f85fb8638f25…` | `df6f614dd69d…` |

El JSON conserva los IDs completos y los IDs de configuración OCI reportados por Trivy, que no son la misma representación del digest de Docker. Los primeros escaneos usaron exportaciones locales identificadas por SHA-256; el segundo análisis leyó el motor Docker por socket montado de solo lectura, con `--image-src docker`, sin exportar otro tar ni montar el workspace.

## Actualizaciones comprobadas

- **API / zlib1g:** `1:1.3.dfsg+really1.3.1-1+b1` → `1:1.3.dfsg+really1.3.1-1+deb13u1`. Debian confirma esa revisión de seguridad para CVE-2026-85091. El nuevo inventario contiene esa versión y ya no detecta ese aviso. Desaparecen también los pares zlib/CVE-2026-76844 y zlib/CVE-2026-27171. [Debian Security Tracker](https://security-tracker.debian.org/tracker/CVE-2026-85091).
- **Web / libxslt:** `1.1.43-r3` → `1.1.43-r4`. El secdb oficial de Alpine asigna a `r4` los fixes CVE-2026-125350, CVE-2026-87636, CVE-2026-9947 y CVE-2025-10911. Ninguno aparece en el nuevo escaneo. El paquete zlib pasó a `1.4-r0` y desapareció su aviso CVE-2026-4738. [Alpine secdb v3.24](https://secdb.alpinelinux.org/v3.24/main.json).

**Discrepancia conservada:** CVE-2026-76844 figura asociado a zlib en los datos del proveedor, pero su descripción habla de webpack. Se conserva como ambigüedad de metadatos; no se declara una vulnerabilidad de webpack en esta imagen ni una cadena de explotación a partir de ese título. [Registro Debian correspondiente](https://security-tracker.debian.org/tracker/CVE-2026-76844).

Esta auditoría verifica versiones instaladas y desaparición de coincidencias concretas tras la reconstrucción. Las pruebas funcionales del servicio reconstruido corresponden al responsable de integración; no se sustituyen por el resultado de Trivy.

## Candidatos residuales de la API

Quedan 206 coincidencias OS, incluidas 47 HIGH repartidas entre 11 CVE distintos. **Ninguna coincidencia residual tiene `FixedVersion` disponible en esta base de datos**. Esto no significa que el riesgo sea cero ni que no exista una corrección futura.

Se consultaron además los once registros primarios de Debian Security Tracker: sus filas de paquete fuente para trixie siguen marcadas `vulnerable`, sin una fila corregida para esa versión de Debian en la consulta realizada. Las versiones y URLs de cada comprobación se conservan en `residual_primary_vendor_checks` del JSON. Esa confirmación del proveedor tampoco demuestra alcanzabilidad desde una petición de esta API.

| Familia fuente | CVE HIGH residuales |
| --- | --- |
| util-linux | CVE-2026-76642, CVE-2026-78408, CVE-2026-78409, CVE-2026-78410 |
| acl | CVE-2026-54369 |
| ncurses | CVE-2025-69720 |
| sqlite | CVE-2026-119373, CVE-2026-119374, CVE-2026-119379 |
| systemd | CVE-2026-16742 |
| perl / Archive-Tar | CVE-2026-9538 |

No se ha demostrado que una petición de la aplicación alcance las funciones afectadas o cumpla sus prerrequisitos de archivos, herramientas, privilegios o configuración. Se requiere triage de cada familia antes de asignarle la severidad de una vulnerabilidad de la aplicación. No se ocultaron avisos sin parche ni se eliminaron paquetes a ciegas para obtener un informe limpio.

## Método, límites y artefactos

La consulta repetible utilizada después de reconstruir fue:

```text
trivy image --image-src docker --scanners vuln --pkg-types os --skip-db-update --disable-telemetry --cache-dir /cache --timeout 2m --format json --output /reports/RESULTADO.json IMAGEN_LOCAL
```

Se ejecutó dentro del contenedor oficial fijado por digest, `--network none`, raíz de solo lectura y sin privilegios adicionales para el segundo análisis. Los comandos completos y la metadata de la base están en el JSON. El primer intento sobre el tar de API falló por permisos de lectura; se corrigieron únicamente los permisos efectivos del contenedor scanner para leer su archivo de entrada. Ambos análisis iniciales y ambos posteriores terminaron con exit code 0; ese código indica ejecución correcta del scanner, no ausencia de avisos.

El alcance excluye bibliotecas Python/JavaScript, secretos, configuración, host, kernel, pruebas de explotación, VEX y análisis completo de alcanzabilidad. Cero coincidencias OS en la imagen web significa cero avisos en este inventario con esta base/fecha, no una certificación general del producto.

Las dos exportaciones temporales propias fueron eliminadas, a petición del responsable, después de verificar ruta absoluta, tamaño y SHA-256; se liberaron 135.603.200 bytes. La caché propia pasó de `/tmp/haiti-container-audit-20261115/cache` a `/var/tmp/haiti-container-audit-20261115/cache`, comprobando que el destino no existía y que los SHA-256 de metadata y base coincidían antes/después. El tmpfs quedó con 1,9 GB disponibles. No se borraron imágenes, volúmenes ni archivos ajenos; los detalles de ambas operaciones están en el JSON.

Para siguientes reconstrucciones: conservar el digest de la base y del artefacto, repetir el análisis con una base vigente, revisar cambios de avisos del proveedor y validar funcionalidad del mismo build. Los candidatos residuales no se declaran corregidos sin actualización y comprobación posterior.

## Ronda con la aplicación ampliada

El 2026-11-15 se repitió Trivy en las imágenes con QR, relaciones, alias y administración. Se conservaron los mismos inventarios OS: API 206 pares paquete/CVE (47 HIGH, 89 MEDIUM, 65 LOW, 5 UNKNOWN; ningún CRITICAL ni FixedVersion publicado), web cero coincidencias. Los resultados completos y digests están en la etapa `final_application_build_2026_11_15` del JSON. Los cambios posteriores de documentación y comportamiento UI no modifican el inventario OS; no implican una reducción adicional de estos riesgos residuales.
