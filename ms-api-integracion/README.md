# CampusStudy — Servicio API (Grupo 5)

Microservicio **API de entrada, orquestación y matching** del proyecto *CampusStudy*.
Es la **cara pública** del sistema distribuido: recibe las solicitudes del Front (Grupo 6),
las enruta hacia el microservicio responsable, agrega respuestas cuando se necesitan varios
servicios y calcula el **emparejamiento (matching)** entre estudiantes.

- Formato de datos: **JSON**
- Arquitectura: **microservicios**
- Estilo: **REST sobre HTTP** con **envoltura estándar** `data / error / meta`
- Comunicación **asíncrona** de eventos hacia Estadísticas (publicador *fire-and-forget*)
- Base URL: `/api/v1/`

---

## 1. Cómo ejecutar

### Local (sin dependencias externas, modo demo)
El modo demo (`STUBS_ENABLED=true`) levanta la API con datos de ejemplo y **no requiere**
los demás microservicios. Ideal para la demo de integración.

```bash
python -m venv .venv
.venv/Scripts/activate            # Windows
pip install -r requirements.txt
STUBS_ENABLED=true uvicorn main:app --port 8080
```

- Swagger: http://localhost:8080/docs
- Health:  http://localhost:8080/api/v1/health

### Local (contra los microservicios reales)
```bash
cp .env.example .env     # ajusta URLs y JWT_SECRET
uvicorn main:app --port 8080
```

### Docker
```bash
docker compose up --build
```

### Pruebas
```bash
pytest -q
```

---

## 2. Arquitectura

```
                     ┌──────────────────────────────┐
   Front (Grupo 6) ─▶│        API / GATEWAY         │
   Postman / cURL    │  (este servicio, Grupo 5)    │
                     │  · orquestación  · matching  │
                     │  · envoltura     · resiliencia│
                     └───────────────┬──────────────┘
                          REST (JSON)│        evento async (fire-and-forget)
        ┌───────────────┬────────────┼─────────────┬───────────────┐
        ▼               ▼            ▼             ▼               ▼
  User-Autent.      Materias      Tareas        Grupos     Notificaciones
   (Grupo 8)         (Grupo 9)    (Grupo 1)    (Grupo 2)      (Grupo 7)
    :8081             :8083        :8085        :8082          :3000
                                                      │
                                                      ▼
                                                Estadísticas (Grupo 4) :8000
                                                POST /api/v1/eventos
```

Regla del contrato: **si un servicio cae, los demás siguen funcionando**. El gateway
aísla los fallos con *timeout*, *reintentos*, *circuit breaker*, *caché* y *degradación parcial*.

---

## 3. Envoltura estándar de respuesta

Toda respuesta (éxito o error) usa la misma envoltura propuesta por el Grupo 5:

```json
{
  "data": {},
  "error": null,
  "meta": { "request_id": "abc-123", "timestamp": "2026-09-16T10:30:00Z" }
}
```

Error:
```json
{
  "data": null,
  "error": { "codigo": 404, "mensaje": "Tarea no encontrada", "detalle": "tarea_id=999 no existe" },
  "meta": { "request_id": "abc-123", "timestamp": "2026-09-16T10:30:00Z" }
}
```

El `request_id` se toma del header `X-Request-ID` entrante o se genera (UUID) y se devuelve
en la respuesta para trazabilidad entre servicios.

---

## 4. Catálogo de endpoints

Todas las rutas modifican datos requieren `Authorization: Bearer <token>`.

| Área | Método | Endpoint | Descripción |
|---|---|---|---|
| Autorización | POST | `/api/v1/auth/login` | Autentica y emite token (delega en User-Autenticación) |
| Autorización | POST | `/api/v1/auth/registro` | Registro de usuario (delega en User-Autenticación) |
| Autorización | POST | `/api/v1/auth/refresh` | Renueva el token |
| Autorización | POST | `/api/v1/auth/logout` | Invalida la sesión (204) |
| Autorización | GET | `/api/v1/auth/me` | Perfil del usuario autenticado |
| Usuarios | GET | `/api/v1/usuarios/{usuario_id}` | Perfil del usuario |
| Usuarios | GET | `/api/v1/usuarios/{usuario_id}/materias` | Materias del estudiante |
| Usuarios | GET | `/api/v1/usuarios/{usuario_id}/tareas` | Tareas del estudiante |
| Usuarios | GET | `/api/v1/usuarios/{usuario_id}/grupos` | Grupos del estudiante |
| Usuarios | GET | `/api/v1/usuarios/{usuario_id}/resumen` | Agregado (perfil+materias+tareas+grupos) |
| Materias | GET | `/api/v1/materias?semestre=&termino=&usuario_id=` | Lista materias |
| Materias | GET | `/api/v1/materias/{materia_id}` | Detalle de materia |
| Tareas | GET | `/api/v1/tareas?usuario_id=&materia_id=&grupo_id=&estado=&fecha_limite=` | Lista tareas |
| Tareas | POST | `/api/v1/tareas` | Crear tarea (201) |
| Tareas | GET | `/api/v1/tareas/{tarea_id}` | Detalle de tarea |
| Tareas | PUT | `/api/v1/tareas/{tarea_id}` | Actualizar tarea |
| Tareas | DELETE | `/api/v1/tareas/{tarea_id}` | Eliminar tarea (204) |
| Grupos | GET | `/api/v1/grupos?materia_id=` | Lista grupos |
| Grupos | POST | `/api/v1/grupos` | Crear grupo (201) |
| Grupos | GET | `/api/v1/grupos/{grupo_id}` | Detalle e integrantes |
| Grupos | POST | `/api/v1/grupos/{grupo_id}/integrantes` | Agregar integrante (201) |
| Grupos | DELETE | `/api/v1/grupos/{grupo_id}/integrantes/{usuario_id}` | Retirar integrante (204) |
| Notificaciones | GET | `/api/v1/notificaciones?usuario_id=&solo_no_leidas=` | Lista notificaciones |
| Notificaciones | POST | `/api/v1/notificaciones` | Publicar notificación (201) |
| Notificaciones | PATCH | `/api/v1/notificaciones/{notificacion_id}` | Marcar como leída |
| Notificaciones | POST | `/api/v1/notificaciones/marcar-todas?usuario_id=` | Marcar todas como leídas |
| Estadísticas | GET | `/api/v1/estadisticas/usuario/{usuario_id}` | Indicadores del estudiante |
| Estadísticas | GET | `/api/v1/estadisticas/materia/{materia_id}` | Indicadores de materia |
| Estadísticas | GET | `/api/v1/estadisticas/grupo/{grupo_id}` | Indicadores de grupo |
| Matching | GET | `/api/v1/match/companeros?materia_id=&habilidad=` | Sugerir compañeros con % de coincidencia |
| Matching | GET | `/api/v1/match/sugerencias/{usuario_id}` | Sugerencias generales |
| Matching | POST | `/api/v1/match/{usuario_id}/solicitud` | Enviar solicitud (202) + notifica |
| Sistema | GET | `/api/v1/health` | Estado de la API y de cada servicio interno |

---

## 5. Manejo de fallos y resiliencia

Implementado según la sección 10 del contrato:

| Mecanismo | Implementación |
|---|---|
| Timeout | 5 s de lectura / 2 s de conexión (configurable) |
| Reintentos | 2 con backoff exponencial **solo en GET** (idempotentes) |
| Circuit breaker | Tras 3 fallos consecutivos abre 30 s; luego semiabierto → cierre |
| Degradación parcial | Agregados devuelven lo disponible + `meta.warnings` |
| Caché de mitigación | Catálogos (materias) con TTL 60 s |
| “No respuesta ≠ no existe” | Timeout/caída → **503**, nunca 404 |
| request_id | Header `X-Request-ID`, propagado en `meta` |

Códigos: `400, 401, 403, 404, 409, 500, 503`.

---

## 6. Comunicación asíncrona (eventos)

El gateway publica eventos de dominio de forma **asíncrona y no bloqueante** hacia
Estadísticas (`POST /api/v1/eventos`) mediante una cola en memoria con reintentos
(*fire-and-forget*): la respuesta al usuario no espera al evento.

Eventos publicados:

| Evento | Cuándo |
|---|---|
| `tarea.creada` | POST /tareas |
| `tarea.actualizada` | PUT /tareas/{id} (campos) |
| `tarea.estado_cambiado` | PUT /tareas/{id} (cambia `estado`) |
| `tarea.eliminada` | DELETE /tareas/{id} |
| `grupo.creado` | POST /grupos |
| `grupo.miembro_agregado` | POST /grupos/{id}/integrantes |
| `grupo.miembro_retirado` | DELETE /grupos/{id}/integrantes/{usuario_id} |
| `match.solicitud_enviada` | POST /match/{id}/solicitud |

Además, al agregar un integrante o enviar una solicitud de matching, el gateway publica
una **notificación** al usuario destinatario.

---

## 7. Matching (lógica propia del Grupo 5)

`GET /match/companeros?materia_id=&habilidad=` consume el perfil y las habilidades
(Usuarios), las materias compartidas (Materias) y los grupos activos (Grupos), y calcula:

| Criterio | Peso |
|---|---|
| Comparte la materia | 40 |
| Habilidades en común (proporción) | 40 |
| No pertenecer ya al mismo grupo | 10 |
| Cumple el filtro `habilidad` (si se pidió) | 10 |

Resultado: `coincidencia` entero 0–100 + `habilidades_compartidas`, ordenado descendente.

---

## 8. Configuración (`.env`)

| Variable | Default | Descripción |
|---|---|---|
| `AUTH_URL` | `http://localhost:8081` | User-Autenticación (Grupo 8) |
| `GRUPOS_URL` | `http://localhost:8082` | Grupos (Grupo 2) |
| `NOTIFICACIONES_URL` | `http://localhost:3000` | Notificaciones (Grupo 7) |
| `ESTADISTICAS_URL` | `http://localhost:8000` | Estadísticas (Grupo 4) |
| `MATERIAS_URL` | `http://localhost:8083` | Materias (Grupo 9) |
| `TAREAS_URL` | `http://localhost:8085` | Tareas (Grupo 1) |
| `JWT_SECRET` | *(el de auth-service)* | Clave HS256 compartida |
| `GRUPOS_AUTH_MODE` | `jwt` | `jwt` o `demo_id` (Bearer = usuario_id de grupos-service) |
| `STUBS_ENABLED` | `false` | `true` → modo demo sin servicios externos |
| `CIRCUIT_FAIL_THRESHOLD` | `3` | Fallos para abrir el circuito |
| `CIRCUIT_RECOVERY_SECONDS` | `30` | Tiempo abierto del circuito |
| `CACHE_TTL_SECONDS` | `60` | TTL de caché de catálogos |
| `CORS_ORIGINS` | `*` | Orígenes permitidos |

> **Importante:** `JWT_SECRET` debe coincidir con el de `auth-service`
> (por defecto `9a8f7b6c...d0e9f8a`). Si no, todo token será rechazado con 401.

---

## 9. Lo que se tomó de los repositorios de otros grupos

Este servicio se construyó respetando los contratos reales de cada repositorio. Detalle de
lo reutilizado/adaptado:

### User-Autenticación — `github.com/samusplay/auth-service-campusStudy` (Grupo 8)
- **Modelo de JWT**: algoritmo **HS256** y el **secret por defecto** (`9a8f...f8a`), claims
  `sub` (usuario_id), `email`, `rol`. El gateway valida con la **misma clave** (`core/security.py`).
- **Shapes** de `POST /api/v1/auth/login` y `/registro` → adaptador `clients/auth_client.py`
  (`AuthResponse`: `token`, `tipo_token`, `expira_en`, `usuario_id`, `nombre`, `rol`).
- **Adaptación**: el contrato pide el campo `correo` y el servicio expone `email`; el gateway
  acepta `correo` y lo traduce a `email` en el cliente.
- **Gap conocido**: `GET /api/v1/users/{id}` es un *stub* (devuelve `null`); el gateway
  construye el perfil desde los *claims* si el proveedor no lo resuelve.

### Grupos — `github.com/Miguelito1924/GRUPOS` (Grupo 2)
- **Endpoints** `/api/v1/grupos`, `/grupos/{id}`, `/grupos/{id}/integrantes` y shapes
  `GrupoDetalleResponse` / `AgregarIntegranteResponse` → `clients/grupos_client.py`.
- **Autenticación demo**: su `AuthFilter` acepta `Authorization: Bearer <usuario_id>`.
  Por eso existe `GRUPOS_AUTH_MODE=demo_id` para enviar el id en lugar del JWT.
- **Patrón de notificación *fire-and-forget*** (cola en memoria + envío no bloqueante a
  Notificaciones) → replicado en `events/publisher.py` y en el alta de integrantes.
- **Convención de errores** (401/404/409/422/503) → mapeados en `clients/base.py`.

### Notificaciones — `github.com/10Jose/Notification_Service` (Grupo 7)
- **Endpoint y payload** `POST /api/v1/notification/create-notifications`
  (`usuario_id, tipo, titulo, mensaje, estado, fecha_creacion`) → `clients/notificaciones_client.py`.
- **Lectura** `GET /api/v1/notification/{usuario_id}` (devuelve las del día) y su shape
  → normalizado al contrato (`leida` booleano derivado de `estado`).
- **Gaps conocidos**: no expone *marcar como leída* ni *marcar todas* ni `refresh_token`;
  esas operaciones devuelven **501** con envoltura estándar hasta que el proveedor las implemente.

### Estadísticas — `github.com/lauravanesa17/Estadisticas_CampusStudy` (Grupo 4)
- **Modelo de eventos** (`POST /api/v1/eventos`, idempotente por `evento_id`) y **nombres de
  evento** (`tarea.creada`, `tarea.actualizada`, `tarea.estado_cambiado`, `tarea.eliminada`,
  `grupo.creado`, `grupo.miembro_agregado`) → usados por el **publicador asíncrono**.
- **Envoltura** `{exito, datos, mensaje}` y convención de **caché TTL 60 s** → *unwrap* en
  `clients/base.py` y `core/cache.py`.
- **Endpoints** `/api/v1/estadisticas/usuario|materia|grupo` → `clients/estadisticas_client.py`.

### Contrato de Interfaz e Integración v1.0 (Grupo 5 — nosotros)
- Envoltura estándar `data / error / meta`, catálogo de endpoints, códigos de error y reglas
  de resiliencia provienen directamente del contrato (`Contrato_API_Grupo5_CampusStudy`).


---

## 10. Estructura del proyecto

```
ms-api-integracion/
├── main.py                  # app, middleware, handlers, wiring
├── core/
│   ├── config.py            # settings (.env)
│   ├── security.py          # JWT HS256, roles, headers a downstream
│   ├── envelope.py          # envoltura data/error/meta
│   ├── errors.py            # ApiError y handlers 400/401/.../503
│   ├── context.py           # request_id (contextvar)
│   ├── circuit_breaker.py   # circuit breaker por servicio
│   └── cache.py             # caché TTL (catálogos)
├── clients/                 # un cliente por microservicio (adaptadores)
│   └── base.py              # HTTP + reintentos + CB + unwrap
├── events/publisher.py      # publicador asíncrono de eventos (estadísticas)
├── services/matching.py     # lógica de emparejamiento
├── routers/                 # auth, usuarios, materias, tareas, grupos,
│                            # notificaciones, estadisticas, match, health
├── schemas/                 # modelos Pydantic de entrada
├── stubs.py                 # datos demo (modo STUBS_ENABLED)
├── tests/                   # pytest (15 pruebas)
├── Dockerfile / docker-compose.yml
└── .env.example
```
