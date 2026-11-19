def test_crud_tareas(client, auth_headers):
    crear = client.post(
        "/api/v1/tareas",
        json={
            "usuario_id": 25,
            "materia_id": 5,
            "titulo": "Parcial de redes",
            "fecha_entrega": "2026-11-01",
            "hora_entrega": "08:00",
        },
        headers=auth_headers,
    )
    assert crear.status_code == 201
    tarea = crear.json()["data"]
    tarea_id = tarea["tarea_id"]

    listado = client.get("/api/v1/tareas?usuario_id=25", headers=auth_headers)
    assert listado.status_code == 200
    assert any(t["tarea_id"] == tarea_id for t in listado.json()["data"])

    detalle = client.get(f"/api/v1/tareas/{tarea_id}", headers=auth_headers)
    assert detalle.status_code == 200

    actualizar = client.put(f"/api/v1/tareas/{tarea_id}", json={"estado": "en_progreso"}, headers=auth_headers)
    assert actualizar.status_code == 200
    assert actualizar.json()["data"]["estado"] == "en_progreso"

    eliminar = client.delete(f"/api/v1/tareas/{tarea_id}", headers=auth_headers)
    assert eliminar.status_code == 204


def test_tarea_inexistente_404(client, auth_headers):
    respuesta = client.get("/api/v1/tareas/999999", headers=auth_headers)
    assert respuesta.status_code == 404
    assert respuesta.json()["error"]["codigo"] == 404
