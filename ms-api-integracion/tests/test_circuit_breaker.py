from core.circuit_breaker import CircuitBreaker


def test_abre_tras_umbral():
    cb = CircuitBreaker()
    for _ in range(3):
        assert cb.permitir("svc")
        cb.registrar_fallo("svc")
    assert not cb.permitir("svc")
    assert cb.estado_publico("svc") == "abierto"


def test_exito_cierra_circuito():
    cb = CircuitBreaker()
    cb.registrar_fallo("svc")
    cb.registrar_exito("svc")
    assert cb.permitir("svc")
    assert cb.estado_publico("svc") == "cerrado"
