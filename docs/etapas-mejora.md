# Etapas de mejora

Este documento registra las mejoras tecnicas aplicadas despues de la revision del proyecto.

## Etapa 1 - Seguridad de acceso y roles

Estado: completada.

Objetivo:
cerrar el acceso abierto a roles, cursos, documentos y conversaciones.

Cambios aplicados:

- Se agrego validacion de dominio institucional con `ALLOWED_EMAIL_DOMAINS`.
- El rol `docente` ahora requiere que el correo exista en Firestore en `docentes_autorizados`.
- Los estudiantes ya no ven todos los cursos activos.
- Se agrego matricula por codigo con `POST /cursos/inscribir`.
- El detalle de curso, documentos y chat ahora exige ser docente dueno o estudiante matriculado.
- Las conversaciones ahora validan `usuario_id` y `curso_id` antes de reutilizar `conversacion_id`.
- Se agregaron tests de dominio, docente autorizado, matricula y conversacion ajena.

Colecciones usadas:

- `usuarios/{uid}`
- `docentes_autorizados/{email_normalizado}`
- `cursos/{curso_id}`
- `matriculas/{curso_id}_{uid}`
- `conversaciones/{conversacion_id}`

Verificacion:

- Backend: `37 passed`
- Frontend: `npm run lint` sin errores, con una advertencia previa de Fast Refresh.
- Frontend: `npm run build` correcto.

## Etapa 2 - Robustez de documentos e ingesta

Estado: completada.

Objetivo:
evitar archivos huerfanos, colisiones de nombres y fallos de batch al procesar documentos.

Alcance:

- Generar rutas unicas para archivos en Cloud Storage.
- Validar tipo MIME y extension.
- Extraer texto y generar embeddings antes de persistir el documento.
- Borrar el archivo de Cloud Storage si falla la escritura posterior.
- Dividir escritura de chunks en batches seguros para Firestore.
- Validar que el documento eliminado pertenezca al curso de la ruta.
- Agregar tests para upload, cleanup y permisos.

Cambios aplicados:

- Se sanitiza el nombre recibido del archivo.
- Se valida extension contra el tipo MIME declarado.
- Se genera una ruta unica en Cloud Storage por documento.
- Se evita subir a Storage antes de extraer texto y generar embeddings.
- Si falla Firestore despues de subir a Storage, se intenta limpiar el archivo y el documento parcial.
- Los chunks se escriben y eliminan en batches de hasta 450 operaciones.
- La eliminacion valida que el documento pertenezca al curso indicado en la ruta.
- Se agregaron tests para upload correcto, extension incorrecta, cleanup y documento de otro curso.

## Etapa 3 - Limpieza de repositorio y presentacion

Estado: completada.

Objetivo:
reducir ruido del repositorio y dejar la base mas limpia para demos, CI y revision academica.

Cambios aplicados:

- Se removio el instalador `GoogleCloudSDKInstaller.exe` del control de versiones.
- Se removieron logs locales de backend y frontend del control de versiones.
- Se agregaron reglas `.gitignore` para `*.log` y `*.exe`.
- Se elimino `frontend/src/App.jsx`, que era una pantalla bootstrap sin uso desde que `main.jsx` define las rutas reales.
- Se verifico que los textos fuente no contienen mojibake persistido (`Ã`, `Â`, `â`, `ðŸ`); el problema observado venia de la salida de consola.

Verificacion:

- Backend: suite de tests.
- Frontend: lint y build.

## Etapa 4 - Escalabilidad RAG

Estado: completada.

Objetivo:
reducir el riesgo de escanear todos los chunks de un curso y preparar el codigo para migrar a un indice vectorial gestionado.

Cambios aplicados:

- Se agregaron variables de configuracion RAG:
  - `RAG_TOP_K`
  - `RAG_SCORE_MINIMO`
  - `RAG_MAX_CHUNKS_SCAN`
  - `RAG_BACKEND`
- El backend actual se declara como `firestore_scan`.
- La recuperacion ahora aplica `limit()` al query de chunks para evitar lecturas sin cota.
- El ranking local por similitud coseno quedo aislado en helpers internos.
- Se agrego un test que verifica que el limite de escaneo se aplique.

Nota:
esta etapa no reemplaza aun el ranking local por un indice vectorial real. Deja el punto de extension listo para migrar despues a Firestore Vector Search, Vertex AI Vector Search u otro motor vectorial.

Verificacion:

- Backend: suite de tests.
- Frontend: lint y build.

## Etapa 5 - Feedback y analitica docente base

Estado: completada.

Objetivo:
capturar senales de calidad de las respuestas y entregar al docente una primera vista cuantitativa del uso del curso.

Cambios aplicados:

- Se agrego feedback por mensaje con `PATCH /cursos/{curso_id}/chat/mensajes/{mensaje_id}/feedback`.
- El feedback acepta `positivo` o `negativo` y un comentario opcional.
- Solo el usuario dueno del mensaje puede registrar feedback.
- El historial de chat retorna el feedback almacenado.
- Se agrego analitica docente con `GET /cursos/{curso_id}/analytics`.
- La analitica incluye mensajes, conversaciones, documentos, chunks, estudiantes matriculados y conteo de feedback.
- El frontend muestra botones `+ Util` y `- Mejorar` en respuestas del tutor.
- El frontend docente muestra una franja de metricas en el detalle del curso.
- Se agregaron tests para feedback y analitica.

Verificacion:

- Backend: suite de tests.
- Frontend: lint y build.

## Etapa 6 - Quizzes generados por IA

Estado: completada.

Objetivo:
agregar generacion, persistencia, resolucion y correccion automatica de quizzes
a partir del material del curso.

Cambios aplicados:

- Se agregaron endpoints de quizzes por curso.
- Los docentes generan y eliminan quizzes.
- Los estudiantes resuelven intentos y reciben correccion con explicaciones.
- La analitica docente incluye total de quizzes, intentos y promedio de aciertos.

## Etapa 7 - BigQuery Vector Search y modo socratico

Estado: completada.

Objetivo:
mejorar la recuperacion RAG a escala y habilitar un modo pedagogico socratico real.

Cambios aplicados:

- Se agrego `RAG_BACKEND=bigquery_vector` con fallback a `firestore_scan`.
- Los chunks se guardan en Firestore y se indexan en BigQuery para busqueda vectorial.
- El chat acepta `modo: directo | socratico`.
- El frontend permite alternar Directo/Socratico y recuerda la preferencia en sesion.
- La analitica docente reporta mensajes y feedback por modo.
