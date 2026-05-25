from typing import Any, Optional
from pydantic import BaseModel

class ApiResponse(BaseModel):
    code: int = 200
    msg: str = "success"
    data: Optional[Any] = None

    @classmethod
    def ok(cls, data: Any = None, msg: str = "success") -> "ApiResponse":
        return cls(code=200, msg=msg, data=data)

    @classmethod
    def error(cls, code: int = 500, msg: str = "error", data: Any = None) -> "ApiResponse":
        return cls(code=code, msg=msg, data=data)