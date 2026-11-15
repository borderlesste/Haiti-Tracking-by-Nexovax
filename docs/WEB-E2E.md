# Pruebas web reproducibles

Fecha: 2026-11-15. Playwright 1.65.1, Chromium de pruebas, viewport 390 × 844. La ejecución local aislada fue autorizada expresamente por el propietario. No se utilizó su perfil de navegador, GPS físico ni servicios de producción.

## Resultado comprobado

`pnpm exec playwright test --reporter=list,json`: **5 passed**, 0 fallos, 0 omitidas, 0 inestables; 66,02 s incluidos inicio y preparación del entorno. Resumen sin secretos: `web-e2e-results.json`. El JSON completo y las bases sintéticas se conservan solamente en los directorios `.runtime` ignorados por Git.

| Prueba | Evidencia |
| --- | --- |
| Búsqueda pública y QR | Consulta sin cuenta/GPS, ficha demo explícita, QR con ruta pública, Escape y foco restaurado |
| Borrador, edición y retiro | Sin calle/número ni GPS; alias persistidos al reabrir; recibo y retiro final sin controles de edición |
| Envío sin GPS y acceso administrativo | Usuario común bloqueado en admin; envío presencial rechazado y ausencia de propuesta nueva comprobada |
| GPS denegado | Respuesta de dispositivo simulada con código 1; aviso claro y guardado como borrador, sin presencia verificada |
| Revisión presencial y envío | Respuesta de dispositivo ficticia con timestamp actual y precisión; duplicados, resumen, consulta que confirma que aún no existe el aporte y envío posterior a la confirmación |

La consulta independiente de SQLite confirmó un único aporte presencial pendiente, su observación privada y punto elegido, un borrador sin observación después de la denegación, ningún registro del envío bloqueado e integridad de la base. No se aprobaron esos registros ni se publicaron como lugares reales.

Tres recorridos comparten los mismos pasos con CUA y también pasaron allí. El navegador integrado no permitió instalar los simuladores JavaScript de GPS de manera determinista; la ejecución Chromium aislada validó las cinco pruebas. Una captura GPS emulada de CUA no se interpreta como medición física.

## Reproducir

Preparar la aplicación siguiendo el README. Después:

```powershell
pnpm.cmd --dir apps/web exec playwright install chromium
pnpm.cmd --dir apps/web test:e2e
```

El runner inicia por sí mismo `scripts/e2e-server.mjs` y espera la salud de la API detrás del proxy. Los puertos `3001`/`8001` deben estar libres: nunca reutiliza ni termina servidores ajenos. Cada arranque crea un UUID y una base nueva en `apps/api/.runtime/e2e-<uuid>/test.db`. El fixture rechaza identificadores que no sean UUID canónicos y archivos de base existentes; hay regresiones para ambas protecciones. El fixture manual `browser-qa.db` anterior no se reutiliza.

La configuración fija APP_ENV=test, secretos efímeros, correo externo y S3 desactivados, y separa evidencias/salida de datos normales. El lanzador no carga el `.env` de uso normal en modo test. Se conservan los datos sintéticos para diagnosticar fallos; no se ejecuta una limpieza recursiva de directorios del propietario.

El workflow contiene un job E2E con versiones fijadas y límite de tiempo. Su ejecución remota permanece pendiente de comprobar cuota gratuita y límite de gasto de Actions; los pushes de esta entrega incluyen `[skip ci]`. No se suben artifacts de navegador a GitHub. Configuración basada en la [documentación oficial de webServer](https://playwright.dev/docs/test-webserver) y [CI](https://playwright.dev/docs/ci-intro).

## Cobertura que todavía falta

La sección 19.3 completa del maestro incluye más escenarios que estas cinco pruebas. El registro/verificación de correo, moderación completa con publicación/corrección/fusión y ciclo de claves con consumo/revocación tienen pruebas API y evidencia manual previa; su automatización integral de navegador sigue pendiente. También faltan GPS físico, revisión por hablantes nativos, dispositivos reales, accesibilidad formal y CI remoto. Los mocks no validan precisión, presencia física ni disponibilidad del proveedor de geolocalización.
