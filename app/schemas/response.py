from typing import Generic, TypeVar, Optional, List
from pydantic import BaseModel

T = TypeVar("T")

class APIResponse(BaseModel, Generic[T]):
    message: str = "success"
    data: Optional[T] = None

class ValidationErrorDetail(BaseModel):
    field: str
    message: str

class ValidationErrorResponse(BaseModel):
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
    message: str
    data: dict = {}
