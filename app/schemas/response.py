from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    """
    Standard API response wrapper.
    """
    message: str = "success"
    data: Optional[T] = None

class ValidationErrorDetail(BaseModel):
    """
    Structure for a single validation error.
    """
    field: str
    message: str

class ValidationErrorResponse(BaseModel):
    """
    Response schema for validation errors (400 Bad Request).
    """
    message: str = "Validation Error"
    data: List[ValidationErrorDetail]

    model_config = {
        "json_schema_extra": {
            "example": {
                "message": "Validation Error",
                "data": [
                    {
                        "field": "email",
                        "message": "value is not a valid email address; The email address is not valid. It must have exactly one @-sign."
                    },
                    {
                        "field": "password",
                        "message": "Field required"
                    }
                ]
            }
        }
    }

class HTTPErrorResponse(BaseModel):
    """
    Standard schema for other HTTP errors (401, 403, 404).
    """
    message: str
    data: dict = {}
