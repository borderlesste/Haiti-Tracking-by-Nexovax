# Pruebas web reproducibles

Fecha: 2026-11-15. Playwright 1.65.1, Chromium de pruebas, viewport 390 × 844. La ejecución local aislada fue autorizada expresamente por el propietario. No se utilizó su perfil de navegador, GPS físico ni servicios de producción.

## Resultado comprobado

`pnpm exec playwright test --reporter=line,json`: **8 passed**, 0 fallos, 0 omitidas, 0 inestables; 134,85 s incluidos inicio y preparación del entorno. Cubren los nueve escenarios web del §19.3 del maestro. Resumen sin secretos: `web-e2e-results.json`. El JSON completo y las bases sintéticas se conservan solamente en los directorios `.runtime` ignorados por Git.

| Prueba | Evidencia |
| --- | --- |
| Búsqueda pública y QR | Consulta sin cuenta/GPS, ficha demo explícita, QR con ruta pública, Escape y foco restaurado |
| Borrador, edición y retiro | Sin calle/número ni GPS; alias persistidos al reabrir; recibo y retiro final sin controles de edición |
| Envío sin GPS y acceso administrativo | Usuario común bloqueado en admin; envío presencial rechazado y ausencia de propuesta nueva comprobada |
| GPS denegado | Respuesta de dispositivo simulada con código 1; aviso claro y guardado como borrador, sin presencia verificada |
| Revisión presencial y envío | Respuesta de dispositivo ficticia con timestamp actual y precisión; duplicados, resumen, consulta que confirma que aún no existe el aporte y envío posterior a la confirmación |
| Registro y verificación | Cuenta ficticia nueva, enlace del outbox local, canje por acción, token eliminado de la URL, replay rechazado y sesión verificada |
| Moderación y corrección | MFA del staff, aprobar/rechazar/cambios/fusión con motivo; corrección tras login y edición devuelta mantienen destino, intención y código público; ficha aprobada visible en mapa/API, vivienda privada ausente |
| Ciclo de clave API | Aplicación propia, reautenticación, secreto una sola vez, consulta, consumo observado, metadata sin secreto, revocación y `401` posterior |

La consulta independiente de SQLite de la ronda inicial confirmó un aporte presencial pendiente, su observación privada y punto elegido, un borrador sin observación después de la denegación, ningún registro del envío bloqueado e integridad de la base. La ampliación de moderación aprueba únicamente registros ficticios dentro de su base desechable; la base normal permanece sin lugares de demostración.

Los nuevos recorridos detectaron tres fallos reales: pérdida de la consulta al iniciar sesión para corregir una ficha, pérdida de la intención/código al editar una corrección devuelta y callback de zoom de Leaflet después de desmontar el mapa. Están corregidos y comprobados por las regresiones. El servidor además rechaza cambiar el destino de un aporte existente; la prueba API falló antes de la corrección. Todas las pruebas de navegador exigen cero excepciones no capturadas, incluida salida del mapa durante zoom.

Tres recorridos comparten los mismos pasos con CUA y también pasaron allí. El navegador integrado no permitió instalar los simuladores JavaScript de GPS de manera determinista; la ejecución Chromium aislada validó las cinco pruebas. Una captura GPS emulada de CUA no se interpreta como medición física.

## Reproducir

Preparar la aplicación siguiendo el README. Después:

```powershell
pnpm.cmd --dir apps/web exec playwright install chromium
pnpm.cmd --dir apps/web test:e2e
```

El runner inicia por sí mismo `scripts/e2e-server.mjs` y espera la salud de la API detrás del proxy. Los puertos `3001`/`8001` deben estar libres: nunca reutiliza ni termina servidores ajenos. Cada arranque crea un UUID y una base nueva en `apps/api/.runtime/e2e-<uuid>/test.db`. El fixture rechaza identificadores que no sean UUID canónicos y archivos de base existentes; hay regresiones para ambas protecciones. El fixture manual `browser-qa.db` anterior no se reutiliza.

La configuración fija APP_ENV=test, secretos efímeros, correo externo y S3 desactivados, y separa evidencias/salida de datos normales. El lanzador no carga el `.env` de uso normal en modo test. El runner comparte su UUID con el lector del outbox; solo admite enlaces de verificación al origen local esperado. Las credenciales y TOTP fijos pertenecen exclusivamente a las cuentas de prueba. Cuatro pruebas Node comprueban UUID/ruta, destino del outbox y un vector TOTP independiente. Se conservan los datos sintéticos para diagnosticar fallos; no se ejecuta una limpieza recursiva de directorios del propietario.

Cada escenario representa un cliente IPv6 del prefijo reservado de documentación `2001:db8::/32` mediante el proxy loopback expresamente confiado. Así no acumulan artificialmente todos sus accesos en la misma IP. Los límites reales permanecen activos; solo se modifica la cabecera de solicitudes `/v1` al origen local y nunca la del proveedor de teselas.

El workflow contiene un job E2E con versiones fijadas y límite de tiempo. Su ejecución remota permanece pendiente de comprobar cuota gratuita y límite de gasto de Actions; los pushes de esta entrega incluyen `[skip ci]`. No se suben artifacts de navegador a GitHub. Configuración basada en la [documentación oficial de webServer](https://playwright.dev/docs/test-webserver) y [CI](https://playwright.dev/docs/ci-intro).

## Validación que todavía falta

Los nueve escenarios del §19.3 están automatizados localmente. Correo real, almacenamiento privado remoto y el flujo completo sobre HTTPS en el hosting elegido siguen pendientes. También faltan GPS físico, revisión por hablantes nativos, dispositivos reales, accesibilidad formal y CI remoto. Los mocks no validan precisión, presencia física ni disponibilidad del proveedor de geolocalización.
