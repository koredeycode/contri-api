from sqlmodel import SQLModel

class Token(SQLModel):
    """
    Schema for JWT access token.
    """
    access_token: str
    token_type: str

class TokenPayload(SQLModel):
    """
    Schema for decoding JWT payload.
    """
    sub: str | None = None
