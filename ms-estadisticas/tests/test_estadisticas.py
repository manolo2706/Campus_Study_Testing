def _registrar_base(client):
    client.post("/api/v1/eventos", json={
        "evento_id": "m-4",
        "evento": "materia.creada",
        "payload": {"materia_id": 4, "nombre": "Sistemas Distribuidos", "nrc": "12345"},
    })


def _tarea(client, evento_id, tarea_id, estado, fecha, materia_id=4, grupo_id=None, hora=None):
    payload = {
        "tarea_id": tarea_id,
        "usuario_id": 25,
        "materia_id": materia_id,
        "estado": estado,
        "fecha_entrega": fecha,
    }
    if grupo_id is not None:
        payload["grupo_id"] = grupo_id
    if hora is not None:
        payload["hora_entrega"] = hora
    return client.post("/api/v1/eventos", json={
        "evento_id": evento_id,
        "evento": "tarea.creada",
        "payload": payload,
    })


def test_salud(client):
    respuesta = client.get("/salud")
    assert respuesta.status_code == 200
    assert respuesta.json()["servicio"] == "estadisticas"


def test_reporte_usuario_cumple_contrato_frontend(client):
    _registrar_base(client)
    _tarea(client, "t-15", 15, "completada", "2026-12-01", hora="18:00")
    _tarea(client, "t-16", 16, "pendiente", "2026-12-20")

    respuesta = client.get("/api/v1/estadisticas/me")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["usuario_id"] == 25
    assert isinstance(cuerpo["usuario_id"], int)
    assert cuerpo["nombre"] == "Ana"
    assert cuerpo["tareas"]["total"] == 2
    assert cuerpo["tareas"]["completadas"] == 1
    assert cuerpo["tareas"]["pendientes"] == 1
    assert cuerpo["tareas"]["vencidas"] == 0
    assert cuerpo["tareas"]["porcentaje_completado"] == 50.0
    assert cuerpo["materias"][0]["materia_id"] == 4
    assert cuerpo["materias"][0]["nombre"] == "Sistemas Distribuidos"
    assert "fecha_calculo" in cuerpo
    assert len(cuerpo["fecha_calculo"]) == 10


def test_tarea_vencida_es_conteo_derivado(client):
    _registrar_base(client)
    _tarea(client, "t-vencida", 99, "pendiente", "2026-01-01")
    cuerpo = client.get("/api/v1/estadisticas/me").json()
    assert cuerpo["tareas"]["vencidas"] == 1
    assert cuerpo["tareas"]["pendientes"] == 0
    assert cuerpo["tareas"]["completadas"] == 0


def test_en_progreso_cuenta_como_pendiente_en_el_contrato_del_front(client):
    _registrar_base(client)
    _tarea(client, "t-prog", 40, "en_progreso", "2026-12-01")
    cuerpo = client.get("/api/v1/estadisticas/me").json()
    assert cuerpo["tareas"]["pendientes"] == 1
    assert "en_progreso" not in cuerpo["tareas"]


def test_idempotencia_de_eventos(client):
    _registrar_base(client)
    evento = {
        "evento_id": "mismo",
        "evento": "tarea.creada",
        "payload": {
            "tarea_id": 70,
            "usuario_id": 25,
            "materia_id": 4,
            "estado": "pendiente",
            "fecha_entrega": "2026-12-01",
        },
    }
    primera = client.post("/api/v1/eventos", json=evento)
    segunda = client.post("/api/v1/eventos", json=evento)
    assert primera.json()["duplicado"] is False
    assert segunda.json()["duplicado"] is True
    assert client.get("/api/v1/estadisticas/me").json()["tareas"]["total"] == 1


def test_sin_token_no_entra(client):
    del client.headers["Authorization"]
    respuesta = client.get("/api/v1/estadisticas/me")
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == 401


def test_token_invalido_401(client):
    client.headers["Authorization"] = "Bearer no-es-un-jwt"
    respuesta = client.get("/api/v1/estadisticas/me")
    assert respuesta.status_code == 401
    assert respuesta.json()["codigo"] == 401


def test_otro_usuario_no_ve_tareas_ajenas(client):
    from tests.conftest import token_para

    _registrar_base(client)
    _tarea(client, "t-15", 15, "completada", "2026-12-01")
    client.headers["Authorization"] = f"Bearer {token_para(30, 'Luis')}"
    cuerpo = client.get("/api/v1/estadisticas/me").json()
    assert cuerpo["usuario_id"] == 30
    assert cuerpo["nombre"] == "Luis"
    assert cuerpo["tareas"]["total"] == 0


def test_parametro_invalido_400(client):
    respuesta = client.get("/api/v1/estadisticas/materia/abc")
    assert respuesta.status_code == 400
    assert respuesta.json()["codigo"] == 400


def test_filtro_materia_en_query(client):
    _registrar_base(client)
    client.post("/api/v1/eventos", json={
        "evento_id": "m-12",
        "evento": "materia.creada",
        "payload": {"materia_id": 12, "nombre": "Bases de Datos", "nrc": "30210"},
    })
    _tarea(client, "t-a", 1, "completada", "2026-12-01", materia_id=4)
    _tarea(client, "t-b", 2, "pendiente", "2026-12-01", materia_id=12)
    cuerpo = client.get("/api/v1/estadisticas/me?materia_id=4").json()
    assert cuerpo["tareas"]["total"] == 1
    assert cuerpo["materias"][0]["materia_id"] == 4


def test_reporte_grupo(client):
    _registrar_base(client)
    client.post("/api/v1/eventos", json={
        "evento_id": "g-7",
        "evento": "grupo.creado",
        "payload": {
            "grupo_id": 7,
            "nombre": "Grupo de estudio - Sistemas Distribuidos",
            "materia_id": 4,
            "integrantes": [{"usuario_id": 25}],
        },
    })
    _tarea(client, "t-g", 55, "completada", "2026-10-10", grupo_id=7)
    cuerpo = client.get("/api/v1/estadisticas/grupo/7").json()
    assert cuerpo["grupo_id"] == 7
    assert cuerpo["integrantes"] == 1
    assert cuerpo["tareas"]["completadas"] == 1


def test_grupo_ajeno_404(client):
    from tests.conftest import token_para

    client.post("/api/v1/eventos", json={
        "evento_id": "g-7",
        "evento": "grupo.creado",
        "payload": {
            "grupo_id": 7,
            "nombre": "Grupo cerrado",
            "materia_id": 4,
            "integrantes": [{"usuario_id": 25}],
        },
    })
    client.headers["Authorization"] = f"Bearer {token_para(30, 'Luis')}"
    respuesta = client.get("/api/v1/estadisticas/grupo/7")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == 404


def test_filtro_periodo(client):
    _registrar_base(client)
    _tarea(client, "t-1", 1, "pendiente", "2026-11-05")
    _tarea(client, "t-2", 2, "pendiente", "2026-12-05")
    cuerpo = client.get("/api/v1/estadisticas/me?periodo=2026-11").json()
    assert cuerpo["periodo"] == "2026-11"
    assert cuerpo["tareas"]["total"] == 1


def test_periodo_invalido_400(client):
    assert client.get("/api/v1/estadisticas/me?periodo=2026-1").status_code == 400


def test_reporte_materia(client):
    _registrar_base(client)
    _tarea(client, "t-m", 5, "completada", "2026-10-10")
    respuesta = client.get("/api/v1/estadisticas/materia/4")
    assert respuesta.status_code == 200
    cuerpo = respuesta.json()
    assert cuerpo["nombre"] == "Sistemas Distribuidos"
    assert cuerpo["tareas"]["porcentaje_completado"] == 100.0


def test_materia_ajena_404(client):
    from tests.conftest import token_para

    _registrar_base(client)
    _tarea(client, "t-m", 5, "completada", "2026-10-10")
    client.headers["Authorization"] = f"Bearer {token_para(30, 'Luis')}"
    respuesta = client.get("/api/v1/estadisticas/materia/4")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == 404


def test_ruta_inexistente_usa_formato_de_error(client):
    respuesta = client.get("/api/v1/no-existe")
    assert respuesta.status_code == 404
    assert respuesta.json()["codigo"] == 404
