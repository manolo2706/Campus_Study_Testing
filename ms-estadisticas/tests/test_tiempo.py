from datetime import datetime, timezone

from app.services.tiempo import ZONA_COLOMBIA, ahora, estado_efectivo


def _evento_tarea(client, fecha, hora=None):
    payload = {
        "tarea_id": 1,
        "usuario_id": 25,
        "materia_id": 4,
        "estado": "pendiente",
        "fecha_entrega": fecha,
    }
    if hora:
        payload["hora_entrega"] = hora
    client.post("/api/v1/eventos", json={"evento_id": "t", "evento": "tarea.creada", "payload": payload})


def test_noche_en_colombia_no_adelanta_el_dia(client, reloj):
    # 21:00 en Colombia = 02:00 UTC del día siguiente.
    reloj.momento = datetime(2026, 10, 13, 2, 0, tzinfo=timezone.utc)
    _evento_tarea(client, "2026-10-12")

    cuerpo = client.get("/api/v1/estadisticas/me").json()

    assert cuerpo["fecha_calculo"] == "2026-10-12"
    assert cuerpo["tareas"]["vencidas"] == 0


def test_hora_entrega_se_respeta(client, reloj):
    _evento_tarea(client, "2026-10-12", "18:00")

    reloj.momento = datetime(2026, 10, 12, 17, 59, tzinfo=ZONA_COLOMBIA)
    assert client.get("/api/v1/estadisticas/me").json()["tareas"]["vencidas"] == 0

    reloj.momento = datetime(2026, 10, 12, 18, 1, tzinfo=ZONA_COLOMBIA)
    assert client.get("/api/v1/estadisticas/me").json()["tareas"]["vencidas"] == 1


def test_sin_hora_vence_al_final_del_dia():
    entrega = datetime(2026, 10, 12, 23, 59)
    assert estado_efectivo("pendiente", entrega, datetime(2026, 10, 12, 23, 0)) == "pendiente"
    assert estado_efectivo("pendiente", entrega, datetime(2026, 10, 13, 0, 1)) == "vencida"


def test_ahora_es_hora_colombia_sin_zona(reloj):
    reloj.momento = datetime(2026, 10, 13, 2, 0, tzinfo=timezone.utc)
    momento = ahora()
    assert momento == datetime(2026, 10, 12, 21, 0)
    assert momento.tzinfo is None
