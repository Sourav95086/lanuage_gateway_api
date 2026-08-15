from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from gateway.agent import (
    detect_language,
    regional_to_english,
    english_to_regional
)


# ==================================================
# FASTAPI
# ==================================================

app = FastAPI(
    title="Parakram Language Gateway",
    description="Regional Language ↔ English Translation API",
    version="1.0.0"
)


# ==================================================
# REQUEST SCHEMAS
# ==================================================

class IncomingRequest(BaseModel):
    """
    Citizen → Backend

    Regional language is converted to English.
    """

    message: str
    thread_id: str


class OutgoingRequest(BaseModel):
    """
    Backend → Citizen

    English is converted to the citizen's
    regional language.
    """

    message: str
    thread_id: str
    language: str


# ==================================================
# ROOT
# ==================================================

@app.get("/")
def root():

    return {
        "success": True,
        "message": "Parakram Language Gateway is running 🚀"
    }


# ==================================================
# REGIONAL → ENGLISH
# ==================================================

@app.post("/translate/in")
def translate_in(
    request: IncomingRequest
):

    try:

        # ------------------------------------------
        # Detect language
        # ------------------------------------------

        language = detect_language(
            request.message
        )

        # ------------------------------------------
        # Translate to English
        # ------------------------------------------

        english = regional_to_english(
            request.message
        )

        return {
            "success": True,
            "thread_id": request.thread_id,
            "language": language,
            "translation": english
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ==================================================
# ENGLISH → REGIONAL
# ==================================================

@app.post("/translate/out")
def translate_out(
    request: OutgoingRequest
):

    try:

        regional = english_to_regional(
            request.message,
            request.language
        )

        return {
            "success": True,
            "thread_id": request.thread_id,
            "language": request.language,
            "translation": regional
        }

    except Exception as e:

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )