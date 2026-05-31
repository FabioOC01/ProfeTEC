from fastapi import HTTPException, status


def normalize_email(email: str | None) -> str:
    return (email or "").strip().lower()


def validate_institutional_email(email: str | None, allowed_domains: list[str]) -> str:
    normalized = normalize_email(email)
    if not normalized or "@" not in normalized:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Debes iniciar sesion con tu correo institucional.",
        )

    if "*" in allowed_domains:
        return normalized

    domain = normalized.rsplit("@", 1)[1]
    if domain not in allowed_domains:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo se permite acceso con correo institucional autorizado.",
        )
    return normalized


def get_usuario_o_403(uid: str, db) -> dict:
    doc = db.collection("usuarios").document(uid).get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Usuario no registrado.")
    return doc.to_dict() or {}


def docente_autorizado(email: str, db) -> bool:
    normalized = normalize_email(email)
    if not normalized:
        return False
    doc = db.collection("docentes_autorizados").document(normalized).get()
    return bool(doc.exists)


def get_curso_o_404(curso_id: str, db) -> dict:
    doc = db.collection("cursos").document(curso_id).get()
    if not doc.exists:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Curso no encontrado.")
    data = doc.to_dict() or {}
    data["id"] = doc.id
    return data


def matricula_id(curso_id: str, uid: str) -> str:
    return f"{curso_id}_{uid}"


def estudiante_matriculado(curso_id: str, uid: str, db) -> bool:
    doc = db.collection("matriculas").document(matricula_id(curso_id, uid)).get()
    return bool(doc.exists)


def verificar_acceso_curso(curso_id: str, uid: str, db) -> tuple[dict, dict]:
    curso = get_curso_o_404(curso_id, db)
    usuario = get_usuario_o_403(uid, db)
    rol = usuario.get("rol")

    if rol == "docente":
        if curso.get("docente_id") != uid:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Los docentes solo pueden acceder a sus propios cursos.",
            )
        return curso, usuario

    if rol == "estudiante":
        if not estudiante_matriculado(curso_id, uid, db):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Debes matricularte en este curso para acceder.",
            )
        return curso, usuario

    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Debes completar el onboarding antes de acceder a cursos.",
    )
