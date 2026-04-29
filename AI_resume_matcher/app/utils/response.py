from typing import Any

def success_response(data: Any = None, message: str = "Success", code: int = 0) -> dict:
    return {
        "code": code,
        "message": message,
        "data": data
    }

def error_response(message: str = "Error", code: int = 5000, data: Any = None):
    return {
        "code": code,
        "message": message,
        "data": data
    }