from __future__ import annotations

from clients import auth_client, grupos_client, materias_client
from core.config import settings
from core.errors import NotFound
from core.security import Usuario


def _jaccard(a: list[str], b: list[str]) -> float:
    set_a, set_b = {x.lower() for x in a}, {x.lower() for x in b}
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def calcular_coincidencia(
    *,
    mismo_materia: bool,
    habilidades_compartidas: list[str],
    total_habilidades: int,
    mismo_grupo: bool,
    habilidad_filtro_cumplida: bool = False,
) -> int:
    puntaje = 0.0
    if mismo_materia:
        puntaje += 40.0
    if total_habilidades > 0:
        puntaje += 40.0 * (len(habilidades_compartidas) / total_habilidades)
    if not mismo_grupo:
        puntaje += 10.0
    if habilidad_filtro_cumplida:
        puntaje += 10.0
    return max(0, min(100, round(puntaje)))


async def _perfil(usuario_id: int, headers: dict) -> dict | None:
    if settings.stubs_enabled:
        import stubs

        return stubs.USUARIOS.get(usuario_id)
    return await auth_client.get_usuario(usuario_id)


async def _candidatos_materia(materia_id: int, headers: dict) -> list[dict]:
    if settings.stubs_enabled:
        import stubs

        ids = [uid for uid, mats in stubs.INSCRIPCIONES.items() if materia_id in mats]
        return [stubs.USUARIOS[uid] for uid in ids if uid in stubs.USUARIOS]

    candidatos: dict[int, dict] = {}
    try:
        grupos = await grupos_client.listar(materia_id=materia_id, headers=headers)
    except Exception:
        grupos = []
    for grupo in grupos:
        for integrante in grupo.get("integrantes") or []:
            uid = integrante.get("usuario_id") if isinstance(integrante, dict) else integrante
            if uid and uid not in candidatos:
                perfil = await _perfil(uid, headers)
                if perfil:
                    candidatos[uid] = perfil
    return list(candidatos.values())


async def _grupos_usuario(usuario_id: int, headers: dict) -> set[int]:
    if settings.stubs_enabled:
        import stubs

        return {gid for gid, g in stubs.GRUPOS.items() if usuario_id in (g.get("integrantes") or [])}
    try:
        grupos = await grupos_client.grupos_de_usuario(usuario_id, headers=headers)
    except Exception:
        return set()
    return {g.get("grupo_id") for g in grupos if g.get("grupo_id") is not None}


async def sugerir_companeros(
    usuario: Usuario,
    *,
    materia_id: int,
    habilidad: str | None = None,
    headers: dict | None = None,
) -> list[dict]:
    headers = headers or {}
    usuario_id = usuario.usuario_id
    perfil = await _perfil(usuario_id, headers) if usuario_id else None
    mis_habilidades = (perfil or {}).get("habilidades", []) or list(usuario.claims.get("habilidades", []) or [])

    candidatos = await _candidatos_materia(materia_id, headers)
    mis_grupos = await _grupos_usuario(usuario_id, headers) if usuario_id else set()

    sugerencias: list[dict] = []
    for candidato in candidatos:
        cand_id = candidato.get("usuario_id")
        if cand_id is None or cand_id == usuario_id:
            continue
        cand_habilidades = candidato.get("habilidades", []) or []
        compartidas = sorted(
            {h for h in cand_habilidades if h.lower() in {m.lower() for m in mis_habilidades}},
            key=str.lower,
        )
        if habilidad:
            if habilidad.lower() not in {h.lower() for h in cand_habilidades}:
                continue
        else:
            habilidad = None

        cand_grupos = await _grupos_usuario(cand_id, headers)
        mismo_grupo = bool(mis_grupos & cand_grupos)
        base = mis_habilidades or ["Python", "Java", "Docker", "Redes", "IA"]
        if habilidad and habilidad not in base:
            base = base + [habilidad]

        sugerencias.append(
            {
                "usuario_id": cand_id,
                "nombre": candidato.get("nombre"),
                "materia_id": materia_id,
                "coincidencia": calcular_coincidencia(
                    mismo_materia=True,
                    habilidades_compartidas=compartidas,
                    total_habilidades=len(base),
                    mismo_grupo=mismo_grupo,
                    habilidad_filtro_cumplida=habilidad is not None,
                ),
                "habilidades_compartidas": compartidas,
            }
        )

    sugerencias.sort(key=lambda s: s["coincidencia"], reverse=True)
    return sugerencias


async def sugerencias_generales(usuario: Usuario, headers: dict | None = None) -> list[dict]:
    headers = headers or {}
    usuario_id = usuario.usuario_id
    if settings.stubs_enabled:
        import stubs

        materias = stubs.INSCRIPCIONES.get(usuario_id, [])
    else:
        materias = [m.get("materia_id") for m in await materias_client.materias_estudiante(usuario_id) if m.get("materia_id")]

    resultado: list[dict] = []
    for materia_id in materias:
        resultado.extend(await sugerir_companeros(usuario, materia_id=materia_id, headers=headers))
    resultado.sort(key=lambda s: s["coincidencia"], reverse=True)
    return resultado


async def enviar_solicitud(usuario: Usuario, para_usuario_id: int, headers: dict | None = None) -> dict:
    headers = headers or {}
    if usuario.usuario_id is None:
        raise NotFound("Usuario no identificado", "se requiere token con usuario_id")
    if usuario.usuario_id == para_usuario_id:
        raise NotFound("Solicitud invalida", "no puedes solicitar ser tu propio companero")

    destinatario = await _perfil(para_usuario_id, headers)
    if destinatario is None:
        raise NotFound("Companero no encontrado", f"usuario_id={para_usuario_id} no existe")

    return {
        "de": usuario.usuario_id,
        "para": para_usuario_id,
        "estado": "pendiente",
    }
