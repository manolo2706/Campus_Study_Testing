from fastapi import APIRouter

router = APIRouter(tags=["salud"])


@router.get("/salud")
def salud() -> dict:
    return {
        "servicio": "estadisticas",
        "estado": "ok",
        "mensaje": "Microservicio de estadísticas de CampusStudy en ejecución.",
    }
