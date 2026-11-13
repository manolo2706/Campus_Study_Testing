def test_login_y_me(client):
    respuesta = client.post(
        "/api/v1/auth/login",
        json={"correo": "estudiante@univer.edu.co", "password": "secreto123"},
    )
    assert respuesta.status_code == 200
    data = respuesta.json()["data"]
    assert data["token"]
    assert data["correo"] == "estudiante@univer.edu.co"

    perfil = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {data['token']}"})
    assert perfil.status_code == 200
    assert perfil.json()["data"]["usuario_id"] == 25


def test_login_credenciales_invalidas(client):
    respuesta = client.post(
        "/api/v1/auth/login",
        json={"correo": "nadie@univer.edu.co", "password": "x"},
    )
    assert respuesta.status_code == 401
    assert respuesta.json()["error"]["codigo"] == 401


def test_me_sin_token(client):
    respuesta = client.get("/api/v1/auth/me")
    assert respuesta.status_code == 401
