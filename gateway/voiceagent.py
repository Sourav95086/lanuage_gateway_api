
import os
import uuid
import asyncio
import tempfile
from pathlib import Path

import edge_tts

from fastapi import (
    FastAPI,
    UploadFile,
    File,
    Form,
    HTTPException
)

from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware

from dotenv import load_dotenv
from groq import Groq


# ============================================================
# LOAD ENVIRONMENT VARIABLES
# ============================================================

load_dotenv()


# ============================================================
# GROQ CONFIGURATION
# ============================================================

GROQ_API_KEY = os.getenv("GROQ_API_KEY")

if not GROQ_API_KEY:

    raise ValueError(
        "GROQ_API_KEY not found in environment variables."
    )


groq_client = Groq(
    api_key=GROQ_API_KEY
)


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Parakram Voice Agent",
    description=(
        "Multilingual Voice Agent supporting "
        "English, Hindi, Bengali and Odia."
    ),
    version="1.0.0"
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]

)


# ============================================================
# DIRECTORIES
# ============================================================

BASE_DIR = Path(__file__).resolve().parent

TEMP_AUDIO_DIR = BASE_DIR / "temp_audio"

TEMP_AUDIO_DIR.mkdir(
    exist_ok=True
)


# ============================================================
# SUPPORTED LANGUAGES
# ============================================================

SUPPORTED_LANGUAGES = {

    "english": {
        "name": "English",
        "code": "en",
        "tts_voice": "en-IN-PrabhatNeural"
    },

    "hindi": {
        "name": "Hindi",
        "code": "hi",
        "tts_voice": "hi-IN-MadhurNeural"
    },

    "bengali": {
        "name": "Bengali",
        "code": "bn",
        "tts_voice": "bn-IN-BashkarNeural"
    },

    "odia": {
        "name": "Odia",
        "code": "or",
        "tts_voice": "or-IN-SwaraNeural"
    }

}


# ============================================================
# LANGUAGE ALIASES
# ============================================================

LANGUAGE_ALIASES = {

    # English
    "english": "english",
    "en": "english",

    # Hindi
    "hindi": "hindi",
    "hi": "hindi",

    # Bengali
    "bengali": "bengali",
    "bangla": "bengali",
    "bn": "bengali",

    # Odia
    "odia": "odia",
    "oriya": "odia",
    "or": "odia"

}


# ============================================================
# NORMALIZE LANGUAGE
# ============================================================

def normalize_language(
    language: str | None
) -> str:

    if not language:

        return "English"


    language = language.strip().lower()


    normalized = LANGUAGE_ALIASES.get(
        language
    )


    if normalized is None:

        return "English"


    return SUPPORTED_LANGUAGES[
        normalized
    ]["name"]


# ============================================================
# GET LANGUAGE DATA
# ============================================================

def get_language_data(
    language: str
) -> dict:

    language_key = language.strip().lower()


    normalized_key = LANGUAGE_ALIASES.get(
        language_key
    )


    if normalized_key is None:

        raise HTTPException(

            status_code=400,

            detail=(
                "Unsupported language. "
                "Supported languages are "
                "English, Hindi, Bengali and Odia."
            )

        )


    return SUPPORTED_LANGUAGES[
        normalized_key
    ]


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/")
async def root():

    return {

        "success": True,

        "agent": "Parakram Voice Agent",

        "status": "running",

        "supported_languages": [

            "English",
            "Hindi",
            "Bengali",
            "Odia"

        ]

    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
async def health():

    return {

        "success": True,

        "status": "healthy",

        "agent": "voice-agent"

    }


# ============================================================
# LANGUAGE LIST
# ============================================================

@app.get("/languages")
async def languages():

    return {

        "success": True,

        "languages": [

            {
                "name": data["name"],
                "code": data["code"],
                "tts_voice": data["tts_voice"]
            }

            for data in SUPPORTED_LANGUAGES.values()

        ]

    }


# ============================================================
# GROQ WHISPER
# SYNCHRONOUS TRANSCRIPTION
# ============================================================

def transcribe_audio_sync(
    file_path: str
) -> dict:

    """
    Send audio to Groq Whisper.

    Whisper automatically detects the spoken language.

    We deliberately DO NOT pass a fixed language.
    """

    try:

        with open(
            file_path,
            "rb"
        ) as audio_file:

            transcription = (

                groq_client.audio.transcriptions.create(

                    file=audio_file,

                    model="whisper-large-v3-turbo",

                    response_format="verbose_json"

                )

            )


        # ------------------------------------------------
        # TRANSCRIPTION
        # ------------------------------------------------

        text = (

            getattr(
                transcription,
                "text",
                ""
            )

            or ""

        ).strip()


        # ------------------------------------------------
        # WHISPER DETECTED LANGUAGE
        # ------------------------------------------------

        detected_language = getattr(

            transcription,

            "language",

            None

        )


        return {

            "text": text,

            "detected_language": detected_language

        }


    except Exception as e:

        raise Exception(

            f"Whisper transcription failed: {str(e)}"

        )


# ============================================================
# NORMALIZE WHISPER LANGUAGE
# ============================================================

def normalize_whisper_language(
    language: str | None
) -> str:

    if not language:

        return "English"


    language = language.strip().lower()


    # Whisper can return names or codes.
    #
    # We normalize them into our four supported
    # language names.

    mapping = {

        "english": "English",
        "en": "English",

        "hindi": "Hindi",
        "hi": "Hindi",

        "bengali": "Bengali",
        "bangla": "Bengali",
        "bn": "Bengali",

        "odia": "Odia",
        "oriya": "Odia",
        "or": "Odia"

    }


    return mapping.get(

        language,

        "English"

    )


# ============================================================
# TRANSCRIBE ENDPOINT
# ============================================================

@app.post("/voice/transcribe")
async def transcribe_voice(

    audio: UploadFile = File(...)

):

    temp_path = None


    try:

        # ------------------------------------------------
        # VALIDATE FILE
        # ------------------------------------------------

        if not audio:

            raise HTTPException(

                status_code=400,

                detail="Audio file is required."

            )


        # ------------------------------------------------
        # READ AUDIO
        # ------------------------------------------------

        audio_bytes = await audio.read()


        if not audio_bytes:

            raise HTTPException(

                status_code=400,

                detail="Uploaded audio file is empty."

            )


        # ------------------------------------------------
        # FILE EXTENSION
        # ------------------------------------------------

        original_filename = (

            audio.filename

            or

            "audio.ogg"

        )


        extension = Path(
            original_filename
        ).suffix


        if not extension:

            extension = ".ogg"


        # ------------------------------------------------
        # CREATE TEMP FILE
        # ------------------------------------------------

        temp_filename = (

            f"{uuid.uuid4().hex}"

            f"{extension}"

        )


        temp_path = (

            TEMP_AUDIO_DIR
            / temp_filename

        )


        with open(
            temp_path,
            "wb"
        ) as file:

            file.write(
                audio_bytes
            )


        # ------------------------------------------------
        # WHISPER
        # ------------------------------------------------

        print(
            "\n======================================"
        )

        print(
            "VOICE AGENT - SPEECH TO TEXT"
        )

        print(
            "======================================"
        )

        print(
            "Filename:",
            original_filename
        )

        print(
            "Size:",
            len(audio_bytes),
            "bytes"
        )


        result = await asyncio.to_thread(

            transcribe_audio_sync,

            str(temp_path)

        )


        text = result["text"]

        whisper_language = result[
            "detected_language"
        ]


        # ------------------------------------------------
        # EMPTY TRANSCRIPTION
        # ------------------------------------------------

        if not text:

            raise HTTPException(

                status_code=422,

                detail=(
                    "Could not understand "
                    "the audio."
                )

            )


        # ------------------------------------------------
        # NORMALIZE LANGUAGE
        # ------------------------------------------------

        language = normalize_whisper_language(

            whisper_language

        )


        # ------------------------------------------------
        # GET LANGUAGE CODE
        # ------------------------------------------------

        language_data = get_language_data(
            language
        )


        print(
            "\nDetected language:",
            language
        )

        print(
            "Language code:",
            language_data["code"]
        )

        print(
            "Transcription:",
            text
        )


        # ------------------------------------------------
        # RESPONSE
        # ------------------------------------------------

        return {

            "success": True,

            "text": text,

            "language": language,

            "language_code": language_data[
                "code"
            ],

            "whisper_language": whisper_language,

            "supported_language": (
                language in [
                    "English",
                    "Hindi",
                    "Bengali",
                    "Odia"
                ]
            )

        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "\nTRANSCRIPTION ERROR:"
        )

        print(
            str(e)
        )


        raise HTTPException(

            status_code=500,

            detail=str(e)

        )


    finally:

        # ------------------------------------------------
        # DELETE TEMP FILE
        # ------------------------------------------------

        if (

            temp_path

            and

            temp_path.exists()

        ):

            try:

                temp_path.unlink()

            except Exception:

                pass


# ============================================================
# TEXT TO SPEECH
# ============================================================

async def generate_tts(

    text: str,

    language: str

) -> str:

    # ------------------------------------------------
    # GET LANGUAGE DATA
    # ------------------------------------------------

    language_data = get_language_data(
        language
    )


    voice = language_data[
        "tts_voice"
    ]


    # ------------------------------------------------
    # OUTPUT FILE
    # ------------------------------------------------

    filename = (

        f"tts_"
        f"{uuid.uuid4().hex}.mp3"

    )


    output_path = (

        TEMP_AUDIO_DIR
        / filename

    )


    # ------------------------------------------------
    # EDGE TTS
    # ------------------------------------------------

    print(
        "\n======================================"
    )

    print(
        "VOICE AGENT - TEXT TO SPEECH"
    )

    print(
        "======================================"
    )

    print(
        "Language:",
        language_data["name"]
    )

    print(
        "Voice:",
        voice
    )


    communicate = edge_tts.Communicate(

        text=text,

        voice=voice

    )


    await communicate.save(

        str(output_path)

    )


    return str(output_path)


# ============================================================
# SYNTHESIZE ENDPOINT
# ============================================================

@app.post("/voice/synthesize")
async def synthesize_voice(

    text: str = Form(...),

    language: str = Form(...)

):

    output_path = None


    try:

        # ------------------------------------------------
        # VALIDATE TEXT
        # ------------------------------------------------

        if not text.strip():

            raise HTTPException(

                status_code=400,

                detail="Text cannot be empty."

            )


        # ------------------------------------------------
        # NORMALIZE LANGUAGE
        # ------------------------------------------------

        normalized_language = normalize_language(

            language

        )


        # ------------------------------------------------
        # GENERATE AUDIO
        # ------------------------------------------------

        output_path = await generate_tts(

            text=text,

            language=normalized_language

        )


        # ------------------------------------------------
        # RETURN AUDIO
        # ------------------------------------------------

        return FileResponse(

            path=output_path,

            media_type="audio/mpeg",

            filename="voice_response.mp3",

            background=None

        )


    except HTTPException:

        raise


    except Exception as e:

        print(
            "\nTTS ERROR:"
        )

        print(
            str(e)
        )


        # Clean file if generation failed

        if (

            output_path

            and

            os.path.exists(output_path)

        ):

            try:

                os.remove(
                    output_path
                )

            except Exception:

                pass


        raise HTTPException(

            status_code=500,

            detail=str(e)

        )


# ============================================================
# COMBINED VOICE PIPELINE
# ============================================================

@app.post("/voice/process")
async def process_voice(

    audio: UploadFile = File(...)

):

    """
    Complete voice-processing endpoint.

    Audio
        ↓
    Whisper
        ↓
    Language Detection
        ↓
    Transcription

    This endpoint DOES NOT call the chatbot.

    It only handles voice processing.
    """

    temp_path = None


    try:

        # ------------------------------------------------
        # READ AUDIO
        # ------------------------------------------------

        audio_bytes = await audio.read()


        if not audio_bytes:

            raise HTTPException(

                status_code=400,

                detail="Audio file is empty."

            )


        # ------------------------------------------------
        # EXTENSION
        # ------------------------------------------------

        original_filename = (

            audio.filename

            or

            "audio.ogg"

        )


        extension = Path(
            original_filename
        ).suffix


        if not extension:

            extension = ".ogg"


        # ------------------------------------------------
        # TEMP FILE
        # ------------------------------------------------

        temp_filename = (

            f"{uuid.uuid4().hex}"

            f"{extension}"

        )


        temp_path = (

            TEMP_AUDIO_DIR
            / temp_filename

        )


        with open(

            temp_path,

            "wb"

        ) as file:

            file.write(
                audio_bytes
            )


        # ------------------------------------------------
        # TRANSCRIPTION
        # ------------------------------------------------

        result = await asyncio.to_thread(

            transcribe_audio_sync,

            str(temp_path)

        )


        text = result["text"]

        whisper_language = result[
            "detected_language"
        ]


        if not text:

            raise HTTPException(

                status_code=422,

                detail="Could not understand audio."

            )


        # ------------------------------------------------
        # LANGUAGE
        # ------------------------------------------------

        language = normalize_whisper_language(

            whisper_language

        )


        language_data = get_language_data(

            language

        )


        # ------------------------------------------------
        # LOG
        # ------------------------------------------------

        print(
            "\n======================================"
        )

        print(
            "VOICE PROCESSING COMPLETE"
        )

        print(
            "======================================"
        )

        print(
            "Language:",
            language
        )

        print(
            "Code:",
            language_data["code"]
        )

        print(
            "Text:",
            text
        )


        # ------------------------------------------------
        # RETURN
        # ------------------------------------------------

        return {

            "success": True,

            "text": text,

            "language": language,

            "language_code": language_data[
                "code"
            ],

            "whisper_language": whisper_language

        }


    except HTTPException:

        raise


    except Exception as e:

        print(
            "\nVOICE PROCESSING ERROR:"
        )

        print(
            str(e)
        )


        raise HTTPException(

            status_code=500,

            detail=str(e)

        )


    finally:

        if (

            temp_path

            and

            temp_path.exists()

        ):

            try:

                temp_path.unlink()

            except Exception:

                pass


# ============================================================
# RUN DIRECTLY
# ============================================================
import uvicorn
if __name__ == "__main__":
    uvicorn.run(
        "voiceagent:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        reload=False
    )