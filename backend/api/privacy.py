from __future__ import annotations

from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, Request, Response

from ..privacy import (
    can_see_names,
    clear_names_access_cookie,
    issue_names_access_cookie,
    names_privacy_is_configured,
    password_matches_configured_secret,
)

router = APIRouter()


class NamesAccessLogin(BaseModel):
    password: str


@router.get("/names/session")
def get_names_session(request: Request):
    return {
        "configured": names_privacy_is_configured(),
        "can_see_names": can_see_names(request),
    }


@router.post("/names/session")
def create_names_session(payload: NamesAccessLogin, request: Request, response: Response):
    if not names_privacy_is_configured():
        return {"configured": False, "can_see_names": True}

    if not password_matches_configured_secret(payload.password):
        raise HTTPException(status_code=401, detail="Mot de passe invalide")

    issue_names_access_cookie(response, request)
    return {"configured": True, "can_see_names": True}


@router.delete("/names/session")
def delete_names_session(response: Response):
    clear_names_access_cookie(response)
    return {"configured": names_privacy_is_configured(), "can_see_names": False}
