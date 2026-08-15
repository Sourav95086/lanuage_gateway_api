from pydantic import BaseModel


class LanguageRequest(BaseModel):
    message: str
    thread_id: str


class LanguageResponse(BaseModel):
    success: bool
    translated_text: str
    thread_id: str