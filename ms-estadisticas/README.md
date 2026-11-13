# CampusStudy — Microservicio de Estadísticas

Servicio alineado con el **Contrato de Interfaz e Integración** del equipo Frontend (versión 1.0, `/api/v1/`).

No es dueño de usuarios, materias, tareas ni grupos. Consulta esos servicios cuando están disponibles, guarda una **caché local** y expone reportes agregados.

## Endpoints que consume el Frontend

| Método | Ruta | Uso |
|---|---|---|
| GET | `/api/v1/estadisticas/usuario/{usuario_id}` | Reporte individual |
| GET | `/api/v1/estadisticas/materia/{materia_id}` | Reporte por materia |
| GET | `/api/v1/estadisticas/grupo/{grupo_id}` | Reporte por grupo |

Query opcionales en usuario: `periodo=YYYY-MM` y `materia_id`.

### Respuesta 200 — usuario (schema Zod)

```json
{
  "usuario_id": 25,
  "nombre": "Ana",
  "periodo": "2026-10",
  "tareas": {
    "total": 4,
    "completadas": 2,
    "pendientes": 1,
    "vencidas": 1,
    "porcentaje_completado": 50.0
  },
  "grupos": {
    "total_grupos": 2,
    "grupos_activos": 2
  },
  "materias": [
    { "materia_id": 4, "nombre": "Sistemas Distribuidos", "tareas_completadas": 1, "tareas_total": 2 }
  ],
  "fecha_calculo": "2026-10-12"
}
```

Reglas tomadas del contrato:

- IDs enteros positivos (`usuario_id`, no `usr-01`)
- `snake_case` en español
- fechas `YYYY-MM-DD`
- porcentajes con un decimal
- `vencida` es un **conteo derivado** (la tarea sigue en `pendiente` o `en_progreso` en Tareas)
- `en_progreso` se reporta dentro de `pendientes` para no romper el schema Zod del Frontend
- `cancelada` no entra en los totales

## Errores

```json
{ "codigo": 404, "mensaje": "Usuario no encontrado." }
```

| Código | Cuándo |
|---|---|
| 400 | Parámetro inválido |
| 404 | Usuario, materia o grupo no encontrado |
| 503 | Dependencia caída y sin caché |

Si una dependencia no responde (contrato I.7):

- **Sin datos previos** (usuario nunca visto, o tareas nunca sincronizadas): `503` con el servicio que falló, p. ej. `{"codigo": 503, "mensaje": "...", "dependencia": "tareas-service"}`. No se inventan ceros.
- **Con caché**: `200` con el último dato, marcado como tal. Los campos extra solo aparecen en este caso y Zod los ignora:

```json
{ "...": "...", "en_cache": true, "actualizado_en": "2026-10-12T10:00:00", "dependencias_no_disponibles": ["tareas-service"] }
```

  Además se envía el encabezado `X-Datos-En-Cache: true`.
- Cada servicio se consulta por separado: si Materias falla, Tareas y Grupos se actualizan igual. Cada falla queda en el log (servicio, usuario, hora).
- Si usuarios-service responde `404`, el usuario se quita de la caché y se responde `404`.

Todas las fechas y el cálculo de `vencidas` usan **hora de Colombia (UTC-5)** y respetan `hora_entrega` (sin hora, la tarea vence a las 23:59).

## Cómo ejecutarlo

```bash
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload --port 8000
```

- Dashboard de prueba: http://127.0.0.1:8000
- Swagger: http://127.0.0.1:8000/docs

Al arrancar carga datos de demo (Ana = `usuario_id` 25) para poder mostrar el servicio sin los otros equipos.

Variables opcionales para consultar a los demás microservicios:

```
USUARIOS_SERVICE_URL=http://localhost:8001
MATERIAS_SERVICE_URL=http://localhost:8002
TAREAS_SERVICE_URL=http://localhost:8003
GRUPOS_SERVICE_URL=http://localhost:8004
```

Otras variables:

```
CACHE_TTL_SECONDS=60       # segundos antes de volver a consultar a los demás servicios
HTTP_TIMEOUT_SECONDS=3     # tiempo máximo por llamada
HTTP_REINTENTOS=2          # reintentos ante fallo de conexión
SERVICIO_TOKEN=            # token servicio-a-servicio (si el Frontend no envía Authorization)
```

Llamadas que hace Estadísticas (reenvía el `Authorization` que recibe del Frontend; si no llega, usa `SERVICIO_TOKEN`):

| Servicio | Endpoint | Nota |
|---|---|---|
| usuarios | `GET /api/v1/usuarios/{id}` | |
| tareas | `GET /api/v1/tareas?usuario_id=&pagina=&tamano=` | recorre todas las páginas |
| tareas | `GET /api/v1/tareas/{id}` | solo para tareas nuevas en caché: el listado no trae `grupo_id` ni `hora_entrega` |
| materias | `GET /api/v1/materias?usuario_id=` y `GET /api/v1/materias/{id}` | el filtro por usuario sigue en discusión (sección E) |
| grupos | `GET /api/v1/grupos` | se filtran los grupos donde el usuario es integrante |

## Pendientes para la reunión de integración

- Acordar el token entre servicios (materias y grupos exponen "mis …" según el JWT).
- Pedir a Tareas que el listado incluya `grupo_id` y `hora_entrega` (ahorra una llamada por tarea nueva).
- Los reportes `/materia/{id}` y `/grupo/{id}` solo leen la caché; se llenan con eventos o con consultas de usuarios.

## Pruebas

```bash
python -m pytest
```

Las pruebas congelan el reloj (12-oct-2026 10:00 hora Colombia) y simulan los demás servicios con `httpx.MockTransport`, con la forma exacta del contrato.
