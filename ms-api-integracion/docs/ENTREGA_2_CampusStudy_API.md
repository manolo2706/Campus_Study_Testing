# ENTREGA #2 — CampusStudy
## Servicio **API** (entrada, orquestación e integración) — Grupo 5

- **Asignatura:** Sistemas Distribuidos
- **Proyecto:** CampusStudy — Sistema distribuido de apoyo a la gestión académica estudiantil
- **Servicio:** API (entrada del sistema, orquestación e integración)
- **Integrantes:** Julio Sánchez, Santiago Fonseca, Cesar Cardozo
- **Repositorio:** https://github.com/Santi5253/campusstudy (código en `ms-api-integracion/`)
- **Contrato de referencia:** *Contrato de Interfaz e Integración v1.0 — API (Grupo 5)*

---

## 1. Descripción general de CampusStudy
*(parte común a todos los grupos)*

### 1.1 Nombre del sistema
**CampusStudy** — Sistema distribuido de apoyo a la gestión académica estudiantil.

### 1.2 Descripción del sistema

- **¿Qué es CampusStudy?**
  Una plataforma distribuida para la **gestión centralizada de actividades académicas** de
  estudiantes universitarios: tareas y trabajos, materias, grupos de trabajo, prioridades,
  recordatorios y notificaciones.

- **¿Qué necesidad atiende?**
  Los estudiantes dispersan su información académica entre agendas, hojas de cálculo,
  chat y notas sueltas. CampusStudy la unifica en un solo lugar, con recordatorios y
  seguimiento del rendimiento.

- **¿Quiénes son sus usuarios?**
  Estudiantes (rol principal), docentes y administradores. El **Front (Grupo 6)** es el
  punto de interacción con el usuario.

- **¿Qué funcionalidades ofrece?**
  Registro/autenticación, gestión de materias, gestión de tareas (CRUD + estados),
  grupos de estudio e integrantes, notificaciones/recordatorios, indicadores académicos
  (estadísticas) y **emparejamiento (matching)** de compañeros de estudio.

- **¿Por qué se plantea como sistema distribuido?**
  Porque cada dominio funcional evoluciona, escala y falla de forma independiente.
  Se aplica la regla: **si un servicio cae, los demás siguen funcionando**. Cada
  microservicio tiene su propia base de datos lógica y se comunican por red (REST/JSON).

- **¿Qué servicios lo conforman?**
  Usuarios-Autenticación (Grupo 8), Materias (Grupo 9), Tareas (Grupo 1), Grupos (Grupo 2),
  Estadísticas (Grupo 4), Notificaciones (Grupo 7), Front (Grupo 6), Pruebas de integración
  (Grupo 3) y **API (Grupo 5, este servicio)**.

- **¿Cómo se relacionan entre ellos?**
  Todos pasan por la **API**, que es la entrada única del sistema. La API consume a los
  servicios internos por REST y publica eventos de forma asíncrona hacia Estadísticas.

### 1.3 Planteamiento del problema
El estudiante no cuenta con un mecanismo único para organizar y priorizar sus
actividades académicas ni para encontrar compañeros de estudio afines.

- **Causa:** herramientas aisladas, sin integración ni recordatorios unificados.
- **Consecuencia:** entregas olvidadas, baja planificación, dificultad para formar grupos.
- **Usuarios afectados:** estudiantes, y en menor medida docentes y administradores.

### 1.4 Objetivo general del sistema
Construir una plataforma distribuida que centralice la organización de actividades
académicas, ofreciendo recordatorios, seguimiento del rendimiento y apoyo a la
conformación de grupos de estudio.

### 1.5 Objetivos específicos
1. Gestionar de forma centralizada tareas, materias, grupos y notificaciones del estudiante.
2. Emitir recordatorios oportunos sobre entregas y eventos académicos.
3. Calcular y presentar indicadores de rendimiento académico.
4. Sugerir compañeros de estudio mediante un servicio de emparejamiento.
5. Garantizar la disponibilidad del sistema ante la caída de componentes individuales.

---

## 2. Alcance del sistema distribuido

**CampusStudy sí hace:**
- Organizar tareas, materias, grupos, recordatorios y notificaciones.
- Calcular indicadores académicos y sugerir compañeros de estudio.
- Mantener el sistema operativo aunque un componente falle (degradación parcial).

**CampusStudy no hace:**
- No gestiona pagos, matrículas ni trámites administrativos de la universidad.
- No reemplaza el aula virtual institucional ni el correo institucional.
- No garantiza conectividad/red fuera de los servicios desplegados.

---

## 3. Arquitectura propuesta del sistema distribuido

```
                         Front  (Grupo 6)
                              |
                         REST / JSON
                              v
                 +---------------------------+
                 |   API / Gateway (Grupo 5) |
                 |  entrada + orquestacion   |
                 +------------+--------------+
                              |
     +------------+-----------+-----------+------------+-------------+
     v            v           v           v            v             v
 Usuarios      Materias     Tareas      Grupos    Notificaciones  Estadisticas
 (Grupo 8)     (Grupo 9)    (Grupo 1)  (Grupo 2)    (Grupo 7)     (Grupo 4)
  :8081         :8083        :8085      :8082        :3000         :8000
                                                     ^                ^
                                                     |                |
                                        Grupos ------+                |
                                                                      |
                 API ---- eventos asincronos (fire-and-forget) --------+

  Grupo 3 (Pruebas de integracion) valida la comunicacion a traves de la API.
```

> El diagrama general del sistema (Miro) se entrega de forma compartida; aquí se resume el
> rol de la API como nodo central de integración.

---

## 4. Descripción del servicio asignado
*(parte particular del Grupo 5)*

### 4.1 Nombre del servicio
**Servicio API** (API de entrada, orquestación e integración).
Repositorio: `campusstudy` → carpeta `ms-api-integracion/`.

### 4.2 Propósito
Es la **cara pública y la puerta de entrada** del sistema. Su responsabilidad es doble:
1. **Pasarela / orquestación:** recibe las solicitudes del Front y de otros servicios, las
   enruta al microservicio responsable, agrega respuestas cuando una operación requiere
   varios servicios y devuelve un resultado coherente con una envoltura estándar.
2. **Matching:** implementa el servicio de emparejamiento que, consumiendo la información
   de Usuarios, Materias y Grupos, calcula porcentajes de coincidencia entre estudiantes y
   sugiere compañeros de estudio.

No reemplaza la lógica interna de cada microservicio: no crea tareas por sí mismo (delega
en Tareas), no administra usuarios (delega en Usuarios-Autenticación). Trata a los demás
servicios como **cajas negras** (solo REST + JSON).

### 4.3 Problema particular
El sistema está compuesto por servicios heterogéneos (Java/Spring, Python/FastAPI,
TypeScript/NestJS) con contratos y formatos diversos. Sin una capa intermedia, el Front
tendría que conocer y llamar a todos, manejar sus fallos y sus formatos. El servicio API
resuelve esa **dispersión**: un solo punto de acceso, reglas comunes (autenticación, JSON,
errores, versionamiento) y coordinación entre servicios.

### 4.4 Objetivo del servicio
Unificar el acceso al sistema distribuido y aplicar reglas comunes de integración,
resiliencia y matching, de modo que el Front consuma **una sola API** coherente y que el
sistema tolere fallos parciales.

### 4.5 Alcance

**El servicio sí realiza:**
- Autenticación delegada (login/registro) y perfil del usuario autenticado.
- Orquestación y agregación de datos de varios servicios (p. ej. resumen del usuario).
- Enrutamiento y normalización de tareas, materias, grupos, notificaciones y estadísticas.
- **Matching** de compañeros de estudio con porcentaje de coincidencia.
- Manejo de fallos: timeout, reintentos, circuit breaker, caché y degradación parcial.
- Envoltura estándar `data / error / meta` y trazabilidad con `request_id`.
- Publicación **asíncrona** de eventos hacia Estadísticas.

**El servicio no realiza:**
- No almacena datos de negocio (no tiene base de datos propia de tareas/materias/etc.).
- No implementa la lógica interna de cada microservicio (delega y solo adapta).
- No es el dueño de la emisión del JWT (lo emite Usuarios-Autenticación; la API lo valida).
- No muestra interfaz gráfica (eso corresponde al Front).

---

## 5. Funcionalidades del microservicio
*(alineadas con el contrato de interfaz v1.0)*

| # | Funcionalidad | Endpoint(s) |
|---|---|---|
| F1 | Autenticación y sesión | `POST /auth/login`, `POST /auth/registro`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me` |
| F2 | Consulta y agregación de usuario | `GET /usuarios/{id}`, `/usuarios/{id}/materias`, `/usuarios/{id}/tareas`, `/usuarios/{id}/grupos`, `/usuarios/{id}/resumen` |
| F3 | Materias | `GET /materias`, `GET /materias/{id}` |
| F4 | Tareas (CRUD) | `GET/POST /tareas`, `GET/PUT/DELETE /tareas/{id}` |
| F5 | Grupos e integrantes | `GET/POST /grupos`, `GET /grupos/{id}`, `POST /grupos/{id}/integrantes`, `DELETE /grupos/{id}/integrantes/{usuario_id}` |
| F6 | Notificaciones | `GET /notificaciones`, `POST /notificaciones`, `PATCH /notificaciones/{id}`, `POST /notificaciones/marcar-todas` |
| F7 | Estadísticas | `GET /estadisticas/usuario/{id}`, `/materia/{id}`, `/grupo/{id}` |
| F8 | **Matching** | `GET /match/companeros`, `GET /match/sugerencias/{id}`, `POST /match/{id}/solicitud` |
| F9 | Salud del ecosistema | `GET /health` (estado de la API y de cada servicio) |
| F10 | Manejo de fallos y trazabilidad | Timeout, reintentos, circuit breaker, caché, degradación parcial, `request_id` |

Todas las rutas están bajo `/api/v1/` y responden con la envoltura estándar.

---

## 6. Arquitectura particular del microservicio

**Elegida:** microservicio en **Python 3.12 + FastAPI** (asíncrono, ASGI/Uvicorn),
comunicación **REST/JSON**, **sin base de datos de negocio**. Se eligió porque el contrato
sugiere Python por su facilidad para construir APIs, y porque el modelo asíncrono de FastAPI
permite **orquestar llamadas a varios servicios en paralelo** (clave para agregación y
resiliencia).

**Capas (separación de responsabilidades):**

```
  Solicitud (Front)
        |
        v
  [ Routers / Controllers ] ---> [ Services (matching, agregacion) ]
        |                                 |
        |                                 v
        |                        [ Clients / Adaptadores REST ]
        |                                 |
        |                                 v
        |                        ( Servicios internos ) <-- REST
        v
  [ Transversal: Envoltura / Errores / request_id ]
        |
        +--> [ Circuit Breaker + Cache ]
        |
        +--> [ Events Publisher ] -- async --> ( Estadisticas )

  [ Security (JWT) ] y [ Config (Settings) ] alimentan a Routers.
```

| Capa | Carpeta | Responsabilidad |
|---|---|---|
| Controladores | `routers/` | Definir endpoints, validar entrada, armar respuestas |
| Servicios | `services/` | Lógica propia (matching, agregación) |
| Repositorios/Adaptadores | `clients/` | Comunicación con cada microservicio (REST) |
| Modelo/Contratos | `schemas/` | Modelos de entrada/salida (Pydantic) |
| Configuración | `core/config.py` | Variables de entorno |
| Seguridad | `core/security.py` | Validación JWT HS256 y roles |
| Transversal | `core/` | Envoltura, errores, `request_id`, circuit breaker, caché |
| Asincronía | `events/` | Publicador de eventos *fire-and-forget* |
| Pruebas | `tests/` | Pruebas unitarias y de integración |

---

## 7. Flujo del servicio

### 7.1 Login y consulta de perfil
```
Front            API (Grupo 5)         Usuarios-Autenticacion
  |                    |                        |
  | POST /auth/login   |                        |
  |------------------->|  POST /auth/login      |
  |                    |----------------------->|
  |                    |  {usuario_id, token,rol}|
  |                    |<-----------------------|
  | 200 {data, meta}   |                        |
  |<-------------------|                        |
  |                    |                        |
  | GET /auth/me (Bearer)                       |
  |------------------->|  GET /users/{id}       |
  |                    |----------------------->|
  |                    |  perfil                |
  |                    |<-----------------------|
  | 200 {data:perfil}  |                        |
  |<-------------------|                        |
```

### 7.2 Operación agregada (resumen del usuario)
```
Front            API (Grupo 5)     Usuarios  Materias  Tareas  Grupos
  |                   |               |         |        |       |
  | GET /usuarios/25/resumen          |         |        |       |
  |------------------>|  (llamadas en paralelo)  |        |       |
  |                   |-------------->|         |        |       |
  |                   |------------------------>|        |       |
  |                   |-------------------------------->|        |
  |                   |----------------------------------------->|
  |                   |<-- perfil ----------------         |       |
  |                   |<-- materias ---------------         |       |
  |                   |<-- tareas ----------------------     |       |
  |                   |<-- grupos ---------------------------------|
  | 200 {data:{...}, meta:{warnings?}} |         |        |       |
  |<------------------|               |         |        |       |

  Si un bloque falla -> se responde lo disponible + advertencia en meta.warnings
```

### 7.3 Crear tarea y evento asíncrono
```
Front            API (Grupo 5)        Tareas         Publisher(async)   Estadisticas
  |                   |                 |                   |               |
  | POST /tareas      |                 |                   |               |
  |------------------>|  POST /tareas   |                   |               |
  |                   |---------------->|                   |               |
  |                   |  tarea (201)    |                   |               |
  |                   |<----------------|                   |               |
  | 201 {data:tarea}  |                 |                   |               |
  |<------------------|                 |                   |               |
  |                   |  publicar "tarea.creada" (no bloqueante)            |
  |                   |----------------------------------->|               |
  |                   |                                     | POST /eventos |
  |                   |                                     |-------------->|
```

### 7.4 Matching
```
Front            API Matching        Usuarios          Grupos
  |                   |                 |                 |
  | GET /match/companeros?materia_id=5  |                 |
  |------------------>|  perfil/habilidades               |
  |                   |---------------->|                 |
  |                   |  grupos/integrantes               |
  |                   |----------------------------->    |
  |                   |<-----------------------------    |
  |                   |<----------------|                 |
  |                   |  Calcula % de coincidencia        |
  | 200 {data:[{usuario_id, coincidencia, habilidades_compartidas}]}      |
  |<------------------|                 |                 |
```

---

## 8. Problemas de sistemas distribuidos aplicables al servicio

| Problema | Qué ocurre | Cómo lo enfrenta la API |
|---|---|---|
| **Latencia** | Un servicio interno tarda en responder | Timeout de 5 s (configurable); si vence → 503. Agregados en paralelo para reducir latencia |
| **Fallo del servicio** | Un microservicio deja de responder | Timeout + reintentos (solo GET) + **503** (nunca 404); degradación parcial en agregados |
| **Fallo de red** | Se pierde la comunicación | Reintentos con backoff exponencial; circuit breaker |
| **Concurrencia** | Dos usuarios modifican el mismo recurso | La API es *stateless*; la validación final la hace el servicio dueño (p. ej. Tareas/Grupos devuelven 409) |
| **Consistencia** | Datos repartidos y desincronizados | Fuente de verdad por dominio; eventos asíncronos hacia Estadísticas; la API no replica datos |
| **Disponibilidad** | Un componente cae | El resto sigue operando; `/health` reporta el estado por servicio; caché de catálogos (TTL 60 s) |
| **Escalabilidad** | Aumentan los usuarios | API *stateless* → escalado horizontal; llamadas concurrentes; caché reduce carga |
| **Dependencia** | Depende de otros servicios | Depende de Usuarios, Materias, Tareas, Grupos, Notificaciones y Estadísticas (ver §9) |
| **Seguridad** | Proteger comunicación y acceso | JWT **HS256** validado en la API; `Authorization: Bearer`; CORS configurable; cada servicio con su BD lógica |

**Circuit breaker:** tras 3 fallos consecutivos a un servicio, el circuito se abre 30 s y
responde 503 de inmediato; luego pasa a semiabierto y se cierra al recuperarse.

---

## 9. Relación con otros microservicios

**¿Quién consume mi servicio?**
- El **Front (Grupo 6)** consume todas las operaciones del catálogo (§5).
- El **Grupo 3 (pruebas)** lo usa para validar la integración.
- Otros servicios pueden consumirlo para matching/agregados.

**¿Qué servicios consumo yo?**

| Servicio (proveedor) | Grupo | Qué necesito | Qué envío | Qué recibo | Por qué lo necesito |
|---|---|---|---|---|---|
| Usuarios-Autenticación | 8 | Validar token, perfil y habilidades | `{email, password}` / `Bearer` | `usuario_id, nombre, rol, token` | Autenticar, autorizar y alimentar el matching |
| Materias | 9 | Catálogo e inscripciones | `usuario_id` | `materia_id, nombre, codigo, semestre` | Filtrar materias y matching |
| Tareas | 1 | CRUD de tareas | JSON de tarea | `{tarea_id, estado, ...}` | Funcionalidad de tareas |
| Grupos | 2 | Grupos e integrantes | JSON de grupo / `usuario_id` | `GrupoDetalleResponse` | Grupos y matching |
| Notificaciones | 7 | Publicar/leer avisos | `{usuario_id, tipo, mensaje}` | notificaciones | Recordatorios y solicitudes de matching |
| Estadísticas | 4 | Indicadores | `GET` / evento `POST /eventos` | métricas | Panel de rendimiento + ingesta de eventos |

---

## 10. Construcción del microservicio

### 10.1 Estructura del proyecto
```
ms-api-integracion/
├── main.py                  # app FastAPI, middleware, handlers, wiring
├── core/                    # config, seguridad, envoltura, errores, request_id, CB, caché
├── routers/                 # controllers: auth, usuarios, materias, tareas, grupos,
│                            #   notificaciones, estadisticas, match, health
├── services/                # lógica propia (matching, agregación)
├── clients/                 # adaptadores REST por microservicio (+ base con reintentos/CB)
├── schemas/                 # modelos Pydantic (contratos de entrada)
├── events/                  # publicador asíncrono de eventos
├── stubs.py                 # datos demo (modo STUBS_ENABLED)
├── tests/                   # pruebas (pytest)
├── requirements.txt
├── Dockerfile / docker-compose.yml
└── README.md
```
Conserva la separación de responsabilidades solicitada
(`controller/service/repository/model/config/tests`), adaptada a FastAPI:
`routers`↔controller, `services`↔service, `clients`↔repository, `schemas`↔model,
`core/config.py`↔config, `tests`↔tests.

### 10.2 API funcional
Primera versión funcional de todos los endpoints del contrato. Ejecución:

```bash
python -m venv .venv && .venv/Scripts/activate
pip install -r requirements.txt
STUBS_ENABLED=true uvicorn main:app --port 8080   # modo demo (sin servicios externos)
# o, contra servicios reales:
cp .env.example .env && uvicorn main:app --port 8080
```
- Swagger: `http://localhost:8080/docs`
- Health: `http://localhost:8080/api/v1/health`

---

## 11. Pruebas

### 11.1 Pruebas automatizadas (unitarias y de integración)
`pytest -q` → **15 pruebas**. Cubren:

| Cobertura exigida | Prueba |
|---|---|
| Funcionamiento de endpoints | `test_tareas` (CRUD), `test_matching`, `test_health` |
| Respuestas correctas | `test_envelope` (envoltura `data/error/meta`) |
| Errores | `test_envelope` (401 sin token, 400 validación), `test_tareas` (404) |
| Servicio no disponible | `test_circuit_breaker` (apertura/cierre) + regla 503≠404 |
| Envío/recepción de información | `test_auth` (login/me), `test_matching` |
| Integración básica | flujo login → me → match → tareas en modo demo |

### 11.2 Pruebas del sistema distribuido (integración con otros grupos)
Guion de validación (contrato §12):

1. **Caso feliz:** `POST /auth/login` → token; `GET /auth/me`; `GET /usuarios/25/materias`;
   `GET /tareas?usuario_id=25`; `POST /tareas` (201); `GET /match/companeros?materia_id=5`;
   `POST /match/25/solicitud` (verifica notificación publicada).
2. **Caso de error:** `GET /tareas/999`→404; `POST /tareas` sin `titulo`→400 con `error.detalle`;
   `GET /auth/me` sin token→401.
3. **Caso de fallo:** detener Tareas → `GET /tareas`→**503** (no 404); reiniciar → el circuito
   se cierra y responde 200; validar `GET /health`.
4. **Criterios comunes:** fechas `YYYY-MM-DD` / `HH:MM`, `snake_case`, ids `{recurso}_id` y
   envoltura estándar en todas las respuestas.

---

## 12. Documentación técnica (README)
El `README.md` del servicio permite a otro miembro del curso:

1. **Instalar:** venv + `pip install -r requirements.txt` (o Docker).
2. **Configurar:** variables de `.env` (URLs de servicios, `JWT_SECRET`, `STUBS_ENABLED`).
3. **Ejecutar:** `uvicorn main:app` o `docker compose up`.
4. **Conocer los endpoints:** catálogo completo en el README y en `/docs` (Swagger).
5. **Probarlo:** guion de integración con cURL/Postman y modo demo.
6. **Conocer sus dependencias:** §9 de este documento y §9 del README (qué se reutilizó de
   cada repositorio de los demás grupos).

---

## Anexo — Trazabilidad con repositorios de otros grupos
- **Usuarios-Autenticación:** JWT HS256 y secret compartido, claims `sub/email/rol`;
  adaptación `correo`↔`email`.
- **Grupos:** endpoints y shapes; `AuthFilter` demo (`Bearer <usuario_id>`); patrón de
  notificación no bloqueante.
- **Notificaciones:** endpoint/payload `create-notifications` y lectura por usuario.
- **Estadísticas:** modelo de eventos `POST /api/v1/eventos` y nombres de evento; unwrap
  `{exito, datos}`; caché TTL 60 s.
