from sqlmodel import SQLModel

class Token(SQLModel):
    access_token: str
    token_type: str

class TokenPayload(SQLModel):
    sub: str | None = None
