from services.matching import calcular_coincidencia


def test_coincidencia_maxima():
    puntaje = calcular_coincidencia(
        mismo_materia=True,
        habilidades_compartidas=["Python", "Docker"],
        total_habilidades=2,
        mismo_grupo=False,
    )
    assert puntaje == 90


def test_coincidencia_sin_habilidades():
    puntaje = calcular_coincidencia(
        mismo_materia=True,
        habilidades_compartidas=[],
        total_habilidades=3,
        mismo_grupo=True,
    )
    assert puntaje == 40


def test_companeros(client, auth_headers):
    respuesta = client.get("/api/v1/match/companeros?materia_id=5", headers=auth_headers)
    assert respuesta.status_code == 200
    companeros = respuesta.json()["data"]
    ids = {c["usuario_id"] for c in companeros}
    assert 30 in ids or 41 in ids
    assert all(0 <= c["coincidencia"] <= 100 for c in companeros)
    coincidencias = [c["coincidencia"] for c in companeros]
    assert coincidencias == sorted(coincidencias, reverse=True)


def test_sugerencias_usuario(client, auth_headers):
    respuesta = client.get("/api/v1/match/sugerencias/25", headers=auth_headers)
    assert respuesta.status_code == 200
    assert isinstance(respuesta.json()["data"], list)
