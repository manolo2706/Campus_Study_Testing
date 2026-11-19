def _envelope(response):
    body = response.json()
    assert set(body.keys()) == {"data", "error", "meta"}
    assert "request_id" in body["meta"]
    assert "timestamp" in body["meta"]
    return body


def test_health(client):
    respuesta = client.get("/api/v1/health")
    assert respuesta.status_code == 200
    body = _envelope(respuesta)
    assert body["error"] is None
    assert body["data"]["api"] == "ok"


def test_request_id_echo(client):
    respuesta = client.get("/api/v1/health", headers={"X-Request-ID": "abc-123"})
    assert respuesta.headers["X-Request-ID"] == "abc-123"
    assert respuesta.json()["meta"]["request_id"] == "abc-123"


def test_error_envelope_sin_token(client):
    respuesta = client.get("/api/v1/tareas")
    assert respuesta.status_code == 401
    body = _envelope(respuesta)
    assert body["data"] is None
    assert body["error"]["codigo"] == 401


def test_validacion_400(client, auth_headers):
    respuesta = client.post("/api/v1/tareas", json={"titulo": "x"}, headers=auth_headers)
    assert respuesta.status_code == 400
    body = _envelope(respuesta)
    assert body["error"]["codigo"] == 400
    assert "detalle" in body["error"]
