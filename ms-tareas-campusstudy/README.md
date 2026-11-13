# Microservicio de Tareas — CampusStudy

Grupo #1, asignatura Sistemas Distribuidos (UNIMINUTO).
Implementa el **Contrato de Interfaz e Integración v1.0** del servicio de Tareas,
con la capa de integración lista para conectarse con los demás microservicios.

- Lenguaje: Python 3.12 (no usar 3.15: aún no hay versiones compiladas de pydantic-core)
- Framework: FastAPI
- Base de datos: MySQL 8
- API: `/api/v1/`

**Estado:** las 7 operaciones del contrato están implementadas y la capa de integración
con los demás microservicios está lista. 39 pruebas automáticas (22 del contrato y 17 de
integración), todas pasando.

```bash
git clone https://github.com/<usuario>/ms-tareas-campusstudy.git
cd ms-tareas-campusstudy
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
copy .env.example .env                            # y ajustar la clave de MySQL
uvicorn app.main:app --reload --port 8001
```

Documentación interactiva en http://localhost:8001/docs

---

## 1. Requisitos

- Python 3.12 (3.13 también sirve; con 3.15 falla la instalación de dependencias)
- MySQL 8 (XAMPP, MySQL Server o Docker)
- Visual Studio Code con la extensión **Python**. Opcional: **REST Client** para ejecutar `docs/pruebas.http`.

## 2. Instalación en Visual Studio Code

```bash
# 1. Abrir la carpeta del proyecto en VS Code
code ms-tareas

# 2. Crear el entorno virtual
python -m venv .venv

# Windows
.venv\Scripts\activate
# Linux o macOS
source .venv/bin/activate

# 3. Instalar las dependencias
pip install -r requirements.txt
```

En VS Code: `Ctrl+Shift+P` → **Python: Select Interpreter** → elegir `.venv`.

## 3. Crear la base de datos

```bash
mysql -u root -p < sql/esquema.sql
```

Si prefieres que las tablas se creen solas, basta con que exista la base de datos
`campusstudy_tareas`: el servicio crea las tablas al arrancar.

## 4. Configurar el archivo .env

```bash
cp .env.example .env     # en Windows: copy .env.example .env
```

Edita `BASE_DATOS_URL` con tu usuario y contraseña de MySQL.

## 5. Ejecutar el servicio

```bash
uvicorn app.main:app --reload --port 8001
```

- Documentación interactiva (Swagger): http://localhost:8001/docs
- Verificación rápida: http://localhost:8001/salud

## 6. Ejecutar las pruebas

```bash
pytest -v
```

Son 39 pruebas: 22 del contrato y 17 de integración. Las de integración levantan
solos los simuladores de los otros servicios, así que tampoco necesitan nada más.
El detalle está en la sección 11.

---

## 7. Operaciones implementadas

| # | Método y endpoint | Descripción | Respuesta |
|---|---|---|---|
| 1 | `POST /api/v1/tareas` | Crear tarea | 201 |
| 2 | `GET /api/v1/tareas/{tarea_id}` | Consultar una tarea | 200 / 404 |
| 3 | `GET /api/v1/tareas?usuario_id=&materia_id=&grupo_id=&estado=&pagina=&tamano=` | Listar con filtros | 200 / 400 |
| 4 | `PUT /api/v1/tareas/{tarea_id}` | Actualizar datos | 200 / 404 |
| 5 | `PUT /api/v1/tareas/{tarea_id}/estado` | Cambiar estado | 200 / 400 |
| 6 | `DELETE /api/v1/tareas/{tarea_id}` | Cancelar (eliminación lógica) | 200 / 404 |
| 7 | `GET /api/v1/tareas/resumen?usuario_id=` | Resumen para Estadísticas | 200 |

Todas exigen el header `Authorization: Bearer <token>`; sin él se responde 401.

**Estructura de respuesta**

```json
{ "exito": true, "datos": { }, "mensaje": "Operación realizada correctamente" }
{ "exito": false, "error": { "codigo": 404, "tipo": "RECURSO_NO_ENCONTRADO", "mensaje": "..." } }
```

**Transiciones de estado**

```
pendiente → en_progreso → completada
pendiente / en_progreso → cancelada
completada y cancelada son estados finales
```

---

## 8. Integración con los otros microservicios

El servicio ya hace llamadas reales por HTTP a los cuatro servicios con los que se
relaciona. Lo que hay que ajustar para la integración está todo en el archivo `.env`.

### 8.1 Qué servicios consultamos

| Proveedor | Variable de URL | Variable de ruta | Para qué |
|---|---|---|---|
| Usuarios (#8) | `URL_USUARIOS` | `RUTA_USUARIO` | Verificar que el estudiante exista y esté activo |
| Materias (#9) | `URL_MATERIAS` | `RUTA_MATERIA` | Verificar que la materia exista |
| Grupos (#2) | `URL_GRUPOS` | `RUTA_GRUPO` | Verificar el grupo y la pertenencia del estudiante |
| Notificaciones (#7) | `URL_NOTIFICACIONES` | `RUTA_NOTIFICACION` | Avisar de los eventos de una tarea |

Si un equipo publica su endpoint con otra ruta, se cambia la variable y listo.
El `{id}` se reemplaza solo.

### 8.2 No importa cómo se llamen sus campos

`app/adaptadores.py` traduce la respuesta de cada servicio al formato del contrato.
Reconoce `usuario_id`, `usuarioId`, `user_id`, `id`; `nombre`, `name`, `nombres`;
`activo`, `active`, `is_active`, `estado`; `integrantes`, `miembros`, `members`.
También desenvuelve respuestas tipo `{"datos": {...}}`, `{"data": {...}}` o una
lista de un solo elemento, y acepta los integrantes como `[1,2,3]` o como
`[{"usuario_id": 1}, ...]`.

Si aparece un nombre que no está contemplado, se agrega a la lista correspondiente
de ese archivo y no hay que tocar nada más.

Para Notificaciones, si ese equipo usa otros nombres, se renombran desde el `.env`
sin tocar el código:

```
NOTIFICACION_MAPA_CAMPOS={"usuario_id": "destinatario", "tipo": "evento"}
```

### 8.3 Token y trazabilidad

Cada llamada saliente lleva el token del estudiante (`PROPAGAR_TOKEN_USUARIO=true`)
y el mismo `X-Request-Id` de la petición original, de modo que una operación se
pueda seguir por todos los servicios con un solo identificador.

Si en la reunión se acuerda que cada servicio valide el token contra Usuarios, se
pone `VALIDAR_TOKEN_CON_USUARIOS=true`. Si lo valida el API Gateway, se deja en
`false`, que es el valor por defecto.

### 8.4 CORS para el Front

El Front (#6) corre en otro origen, así que el navegador exige CORS. Por defecto se
permite cualquier origen; cuando el equipo del Front indique su dirección se pone en
`ORIGENES_PERMITIDOS=http://localhost:3000`.

### 8.5 Idempotencia

Si la conexión se cae después de guardar pero antes de que la respuesta llegue al
Front, el estudiante podría reintentar y crear la tarea dos veces. Para evitarlo, el
Front puede enviar el header `X-Idempotency-Key`: si llega dos veces la misma clave,
se devuelve la tarea ya creada con código 200 en lugar de crear otra.

### 8.6 Ver quién está arriba

```
GET http://localhost:8001/salud/dependencias
```

Devuelve el estado de los cuatro servicios. Es lo primero que conviene revisar el día
de la integración, antes de empezar a buscar errores en el código.

---

## 9. Probar la integración sin esperar a los demás equipos

El proyecto incluye simuladores de los cuatro servicios. Se levantan todos con:

```bash
python mocks/servidores.py
```

| Simulador | Puerto |
|---|---|
| Usuarios | 8008 |
| Materias | 8009 |
| Grupos | 8002 |
| Notificaciones | 8007 |

Las llamadas son de red reales: pasan por los reintentos, los adaptadores y el manejo
de errores. Para la demostración, cada simulador se puede tumbar y restablecer:

```bash
curl -X POST http://localhost:8008/mock/caer
curl -X POST http://localhost:8008/mock/levantar
curl http://localhost:8007/mock/recibidas    # eventos que recibió Notificaciones
```

A propósito, Materias responde con campos planos en inglés (`id`, `name`) y Grupos
envuelve en `data` con `miembros`. Es para comprobar que los adaptadores funcionan
aunque los equipos no usen los mismos nombres.

El archivo `docs/integracion.http` trae las catorce peticiones de la demostración
en orden, listas para ejecutar con la extensión REST Client de VS Code.

### Datos de prueba de los simuladores

| Valor | Resultado |
|---|---|
| `usuario_id`, `materia_id` o `grupo_id` = `999999` | El proveedor responde 404 → Tareas devuelve 400 |
| `usuario_id` = `888888` | Existe pero está inactivo → 400 |
| Grupo 1 | Integrantes `[1, 2, 3, 692464]` |
| Grupo 3 | Integrantes `[692464, 897847, 729495]` |
| Materias | 12 (Sistemas Distribuidos), 13 (Bases de Datos), 14 (Ingeniería de Software) |

---

## 10. Modo simulado interno

Si un equipo todavía no tiene su servicio y tampoco se quieren usar los simuladores,
`SIMULAR_SERVICIOS=true` hace que el servicio responda con datos de prueba sin salir
a la red. Es el modo con el que se entregó la segunda entrega.

---

## 11. Pruebas

```bash
pytest -v                          # las 39 pruebas
pytest tests/test_contrato.py -v   # 22 pruebas del contrato, sin red
pytest tests/test_integracion.py -v  # 17 pruebas de integración por HTTP real
```

Las de integración levantan los simuladores en puertos propios (8802, 8807, 8808,
8809) y hacen peticiones de red de verdad. Verifican la comunicación con cada
servicio, los adaptadores, los errores 400 y 503, la idempotencia y que las consultas
sigan funcionando con todos los proveedores caídos.

El día de la integración real, estas mismas pruebas sirven apuntando las URLs a los
servicios de cada equipo.

---

## 12. Manejo de fallos implementado

- Tiempo de espera de 3 segundos por llamada.
- Dos reintentos, con esperas de 1 y 2 segundos.
- Tras 5 fallos seguidos, el servicio deja de llamar al proveedor por 30 segundos.
- Si Usuarios, Materias o Grupos no responden: la tarea **no** se crea y se devuelve 503.
  Nunca se interpreta "sin respuesta" como "el dato no existe".
- Si Notificaciones no responde: la tarea sí se crea y el evento queda en la tabla
  `eventos_pendientes`, con reintentos cada 5 minutos hasta por 24 horas.
- Las consultas (GET) funcionan siempre, porque solo usan la base de datos propia.

---

## 13. Estructura del proyecto

```
ms-tareas/
├── app/
│   ├── main.py             API, CORS, X-Request-Id y manejo de errores
│   ├── config.py           Configuración leída desde .env
│   ├── contexto.py         Propaga el token y el request_id entre capas
│   ├── database.py         Conexión a MySQL
│   ├── models.py           Tablas: tareas, eventos_pendientes, idempotencia
│   ├── esquemas.py         Validaciones y reglas de datos del contrato
│   ├── servicios.py        Lógica de las operaciones 1 a 7 e idempotencia
│   ├── clientes.py         Llamadas a otros servicios, reintentos y caché
│   ├── adaptadores.py      Traduce las respuestas de los otros equipos
│   ├── notificaciones.py   Envío de eventos y cola de pendientes
│   ├── seguridad.py        Validación del token
│   ├── errores.py          Errores 400, 401, 404, 500 y 503
│   ├── respuestas.py       Estructura estándar de respuesta
│   ├── utilidades.py       Formatos de fecha y hora (UTC-5)
│   └── routers/tareas.py   Endpoints
├── mocks/servidores.py     Simuladores de los otros cuatro servicios
├── sql/esquema.sql
├── tests/
│   ├── test_contrato.py    22 pruebas del contrato
│   └── test_integracion.py 17 pruebas de integración por HTTP
├── docs/pruebas.http
├── docs/integracion.http
├── requirements.txt
└── .env.example
```
