from pydantic import BaseModel


class Principal(BaseModel):
    user_id: str
    organization_id: str | None = None
    is_development_identity: bool = False


class PrincipalResponse(BaseModel):
    data: Principal
