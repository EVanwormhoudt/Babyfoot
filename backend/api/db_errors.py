from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError


def map_integrity_error(exc: IntegrityError, default_message: str = "Erreur d'integrite base de donnees") -> HTTPException:
    """
    Map common PostgreSQL integrity violations to API-friendly status codes.
    """
    orig = getattr(exc, "orig", None)
    sqlstate = getattr(orig, "sqlstate", None) or getattr(orig, "pgcode", None)
    detail = str(orig or exc).lower()

    if sqlstate == "23505" or "duplicate key" in detail or "unique constraint" in detail:
        return HTTPException(status_code=409, detail="La ressource existe deja")

    if sqlstate in {"23503", "23514", "23502", "22P02"}:
        return HTTPException(status_code=422, detail="Les donnees envoyees violent une contrainte de base")

    if "foreign key" in detail or "check constraint" in detail or "not-null constraint" in detail:
        return HTTPException(status_code=422, detail="Les donnees envoyees violent une contrainte de base")

    return HTTPException(status_code=409, detail=default_message)
