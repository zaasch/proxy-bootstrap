import uuid as uuid_mod

from pydantic import BaseModel, Field
from typing import Optional


class ManagerConfig(BaseModel):

    manager_url: str = Field(...)
    uuid: uuid_mod.UUID = Field(...)
    hostname: str = Field(...)
    api_path: str = Field(...)

    class SSOConfig(BaseModel):
        provider_url: str = Field(...)
        registration_path: str = Field(...)
        token_path: str = Field(...)
        client_id: str = Field(...)
        token: Optional[str] = Field(None)
        client_secret: Optional[str] = Field(None)

    sso: SSOConfig = Field(...)
