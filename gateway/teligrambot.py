
import os
import asyncio
import tempfile

import httpx
import edge_tts

from dotenv import load_dotenv
from groq import Groq

from telegram import Update
from telegram.constants import ChatAction

from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters
)


# ==================================================
# LOAD ENVIRONMENT VARIABLES
# ==================================================

load_dotenv()


# ==================================================
# TELEGRAM
# ==================================================

TOKEN = os.getenv(
    "TELEGRAM_BOT_TOKEN"
)

if not TOKEN:
    raise ValueError(
        "TELEGRAM_BOT_TOKEN not found in .env"
    )


# ==================================================
# GROQ
# ==================================================

GROQ_API_KEY = os.getenv(
    "GROQ_API_KEY"
)

if not GROQ_API_KEY:
    raise ValueError(
        "GROQ_API_KEY not found in .env"
    )


groq_client = Groq(
    api_key=GROQ_API_KEY
)


# ==================================================
# LANGUAGE GATEWAY
# ==================================================

LANGUAGE_GATEWAY_URL = os.getenv(
    "LANGUAGE_GATEWAY_URL",
    "https://lanuagegatewayapi-production.up.railway.app"
)


TRANSLATE_IN_URL = (
    f"{LANGUAGE_GATEWAY_URL}/translate/in"
)


TRANSLATE_OUT_URL = (
    f"{LANGUAGE_GATEWAY_URL}/translate/out"
)


# ==================================================
# PARAKRAM API
# ==================================================

PARAKRAM_BASE_URL = (
    "https://parakramuserreportchatbot-production-a5e6.up.railway.app"
)


PARAKRAM_CHAT_URL = (
    f"{PARAKRAM_BASE_URL}/chat"
)


UPLOAD_IMAGE_URL = (
    f"{PARAKRAM_BASE_URL}/upload-image"
)


UPLOAD_VIDEO_URL = (
    f"{PARAKRAM_BASE_URL}/upload-video"
)


# ==================================================
# THREAD / SESSION MANAGEMENT
# ==================================================

# Number of USER messages allowed in one conversation
# thread before automatically creating a new thread.

MAX_MESSAGES_PER_THREAD = 35


# Temporary in-memory storage
#
# {
#     6626297081: {
#         "session": 1,
#         "message_count": 3
#     }
# }

user_sessions = {}


# ==================================================
# LANGUAGE → TTS VOICE
# ==================================================

VOICE_MAP = {

    "English": "en-IN-PrabhatNeural",

    "Hindi": "hi-IN-MadhurNeural",

    "Bengali": "bn-IN-BashkarNeural",

    # Real Odia voice
    "Odia": "or-IN-SwaraNeural",

    # Alias
    "Oriya": "or-IN-SwaraNeural"
}


# ==================================================
# AUDIO LANGUAGE NORMALIZATION
# ==================================================

def normalize_audio_language(
    language: str | None
) -> str:

    """
    Normalize Whisper's detected language
    into the language names used by the bot.

    Supported languages:
        English
        Hindi
        Bengali
        Odia
    """

    if not language:
        return "English"

    language = language.strip().lower()

    language_map = {

        # ------------------------------------------
        # ENGLISH
        # ------------------------------------------

        "english": "English",
        "en": "English",

        # ------------------------------------------
        # HINDI
        # ------------------------------------------

        "hindi": "Hindi",
        "hi": "Hindi",

        # ------------------------------------------
        # BENGALI
        # ------------------------------------------

        "bengali": "Bengali",
        "bangla": "Bengali",
        "bn": "Bengali",

        # ------------------------------------------
        # ODIA
        # ------------------------------------------

        "odia": "Odia",
        "oriya": "Odia",
        "or": "Odia"
    }

    return language_map.get(
        language,
        "English"
    )


# ==================================================
# GET THREAD ID
# ==================================================

def get_thread_id(
    update: Update
) -> str:

    user_id = update.effective_user.id


    # ----------------------------------------------
    # FIRST MESSAGE FROM USER
    # ----------------------------------------------

    if user_id not in user_sessions:

        user_sessions[user_id] = {

            "session": 1,

            "message_count": 0

        }


    user_data = user_sessions[user_id]


    # ----------------------------------------------
    # INCREASE MESSAGE COUNT
    # ----------------------------------------------

    user_data["message_count"] += 1


    # ----------------------------------------------
    # RESET THREAD AFTER N MESSAGES
    # ----------------------------------------------

    if (
        user_data["message_count"]
        > MAX_MESSAGES_PER_THREAD
    ):

        user_data["session"] += 1

        user_data["message_count"] = 1


        print("\n================================")
        print("THREAD RESET")
        print("================================")

        print(
            "User ID:",
            user_id
        )

        print(
            "New Session:",
            user_data["session"]
        )


    # ----------------------------------------------
    # CREATE THREAD ID
    # ----------------------------------------------

    thread_id = (

        f"telegram_{user_id}"
        f"_session_{user_data['session']}"

    )


    print(
        f"\nTHREAD ID: {thread_id}"
    )

    print(
        f"MESSAGE COUNT: "
        f"{user_data['message_count']}"
        f"/{MAX_MESSAGES_PER_THREAD}"
    )


    return thread_id


# ==================================================
# START COMMAND
# ==================================================

async def start(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE
):

    await update.message.reply_text(

        "Hello! 👋\n\n"

        "I am the Parakram Civic Assistant.\n\n"

        "You can send me:\n"

        "• Text\n"
        "• Image\n"
        "• Video\n"
        "• Voice message\n\n"

        "Voice messages can be in:\n"
        "• English\n"
        "• Hindi\n"
        "• Bengali\n"
        "• Odia\n\n"

        "Tell me about any civic issue you are facing."

    )


# ==================================================
# SPEECH → TEXT
# MULTILINGUAL WHISPER
# ==================================================

def transcribe_audio_sync(
    file_path: str
) -> tuple[str, str]:

    """
    Transcribe Telegram voice using Groq Whisper.

    Whisper automatically detects the spoken language.

    Supported:
        English
        Hindi
        Bengali
        Odia
    """

    with open(
        file_path,
        "rb"
    ) as audio_file:

        transcription = (

            groq_client.audio.transcriptions.create(

                file=audio_file,

                model="whisper-large-v3-turbo",

                # IMPORTANT:
                # verbose_json gives us:
                #
                # transcription.text
                # transcription.language
                #
                # We intentionally DO NOT provide
                # a fixed language so Whisper can
                # automatically detect the language.

                response_format="verbose_json"

            )

        )


    # ------------------------------------------
    # GET TRANSCRIPTION
    # ------------------------------------------

    text = (

        getattr(
            transcription,
            "text",
            ""
        )

        or ""

    ).strip()


    # ------------------------------------------
    # GET DETECTED LANGUAGE
    # ------------------------------------------

    detected_language = getattr(
        transcription,
        "language",
        None
    )


    # ------------------------------------------
    # NORMALIZE LANGUAGE
    # ------------------------------------------

    language = normalize_audio_language(
        detected_language
    )


    return (
        text,
        language
    )


# ==================================================
# ASYNC SPEECH → TEXT
# ==================================================

async def speech_to_text(
    file_bytes: bytes
) -> tuple[str, str]:

    """
    Convert audio bytes into:

        (
            transcription,
            detected_language
        )
    """

    temp_path = None


    try:

        # ------------------------------------------
        # CREATE TEMPORARY AUDIO FILE
        # ------------------------------------------

        with tempfile.NamedTemporaryFile(

            suffix=".ogg",

            delete=False

        ) as temp_file:

            temp_file.write(
                file_bytes
            )

            temp_path = temp_file.name


        # ------------------------------------------
        # GROQ SPEECH → TEXT
        # ------------------------------------------

        text, language = await asyncio.to_thread(

            transcribe_audio_sync,

            temp_path

        )


        return (
            text,
            language
        )


    finally:

        # ------------------------------------------
        # DELETE TEMP FILE
        # ------------------------------------------

        if (
            temp_path
            and os.path.exists(temp_path)
        ):

            os.remove(
                temp_path
            )


# ==================================================
# LANGUAGE GATEWAY
# REGIONAL → ENGLISH
# ==================================================

async def translate_to_english(

    message: str,
    thread_id: str

) -> dict:

    payload = {

        "message": message,

        "thread_id": thread_id

    }


    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        response = await client.post(

            TRANSLATE_IN_URL,

            json=payload

        )


    response.raise_for_status()


    return response.json()


# ==================================================
# LANGUAGE GATEWAY
# ENGLISH → REGIONAL
# ==================================================

async def translate_to_regional(

    message: str,
    thread_id: str,
    language: str

) -> dict:

    payload = {

        "message": message,

        "thread_id": thread_id,

        "language": language

    }


    async with httpx.AsyncClient(
        timeout=120.0
    ) as client:

        response = await client.post(

            TRANSLATE_OUT_URL,

            json=payload

        )


    response.raise_for_status()


    return response.json()


# ==================================================
# PARAKRAM CHAT API
# ==================================================

async def send_to_parakram(

    message: str,
    thread_id: str,
    image_url: str | None = None,
    video_url: str | None = None

) -> dict:

    payload = {

        "message": message,

        "thread_id": thread_id,

        "image_url": image_url,

        "video_url": video_url

    }


    print("\n================================")
    print("SENDING REQUEST TO PARAKRAM")
    print("================================")

    print("URL:")

    print(
        PARAKRAM_CHAT_URL
    )


    print("\nPAYLOAD:")

    print(
        payload
    )


    try:

        async with httpx.AsyncClient(
            timeout=180.0
        ) as client:

            response = await client.post(

                PARAKRAM_CHAT_URL,

                json=payload

            )


        print("\n================================")
        print("PARAKRAM RESPONSE")
        print("================================")

        print("STATUS CODE:")

        print(
            response.status_code
        )


        print("\nRESPONSE BODY:")

        print(
            response.text
        )


        if response.status_code >= 400:

            raise Exception(

                f"Parakram API failed\n"

                f"Status: "
                f"{response.status_code}\n"

                f"Response: "
                f"{response.text}"

            )


        return response.json()


    except httpx.RequestError as e:

        raise Exception(

            f"Could not connect to "
            f"Parakram API: {str(e)}"

        )


# ==================================================
# UPLOAD IMAGE
# ==================================================

async def upload_image(

    file_bytes: bytes,
    file_name: str,
    content_type: str

) -> dict:

    files = {

        "image": (

            file_name,

            file_bytes,

            content_type

        )

    }


    async with httpx.AsyncClient(
        timeout=180.0
    ) as client:

        response = await client.post(

            UPLOAD_IMAGE_URL,

            files=files

        )


    response.raise_for_status()


    return response.json()


# ==================================================
# UPLOAD VIDEO
# ==================================================

async def upload_video(

    file_bytes: bytes,
    file_name: str,
    content_type: str

) -> dict:

    files = {

        "video": (

            file_name,

            file_bytes,

            content_type

        )

    }


    async with httpx.AsyncClient(
        timeout=300.0
    ) as client:

        response = await client.post(

            UPLOAD_VIDEO_URL,

            files=files

        )


    response.raise_for_status()


    return response.json()


# ==================================================
# TEXT → SPEECH
# MULTILINGUAL TTS
# ==================================================

async def text_to_speech(

    text: str,
    language: str

) -> str:

    voice = VOICE_MAP.get(

        language,

        "en-IN-PrabhatNeural"

    )


    print(
        "\nTTS LANGUAGE:"
    )

    print(
        language
    )


    print(
        "\nTTS VOICE:"
    )

    print(
        voice
    )


    with tempfile.NamedTemporaryFile(

        suffix=".mp3",

        delete=False

    ) as temp_file:

        temp_path = temp_file.name


    communicate = edge_tts.Communicate(

        text=text,

        voice=voice

    )


    await communicate.save(

        temp_path

    )


    return temp_path


# ==================================================
# COMPLETE MESSAGE PIPELINE
# ==================================================

async def process_message(

    message: str,
    thread_id: str,
    image_url: str | None = None,
    video_url: str | None = None

) -> tuple[str, str]:

    # ----------------------------------------------
    # STEP 1
    # USER LANGUAGE → ENGLISH
    # ----------------------------------------------

    translation_result = (

        await translate_to_english(

            message=message,

            thread_id=thread_id

        )

    )


    language = translation_result.get(

        "language",

        "English"

    )


    english_message = translation_result.get(

        "translation",

        message

    )


    # ----------------------------------------------
    # SAFETY FALLBACK
    # ----------------------------------------------

    if (

        not english_message

        or

        not english_message.strip()

    ):

        english_message = message


    print("\n--------------------------------")

    print("LANGUAGE DETECTED:")

    print(
        language
    )


    print("\nENGLISH MESSAGE:")

    print(
        english_message
    )


    # ----------------------------------------------
    # STEP 2
    # SEND TO PARAKRAM
    # ----------------------------------------------

    parakram_result = (

        await send_to_parakram(

            message=english_message,

            thread_id=thread_id,

            image_url=image_url,

            video_url=video_url

        )

    )


    if not parakram_result.get(

        "success"

    ):

        raise Exception(

            "Parakram chatbot failed"

        )


    english_response = (

        parakram_result.get(

            "response",

            "Sorry, I could not process your request."

        )

    )


    print("\nPARAKRAM ENGLISH RESPONSE:")

    print(
        english_response
    )


    # ----------------------------------------------
    # STEP 3
    # ENGLISH USER
    #
    # NO TRANSLATION REQUIRED
    # ----------------------------------------------

    if language.strip().lower() == "english":

        final_response = english_response


    # ----------------------------------------------
    # STEP 4
    # ENGLISH → USER LANGUAGE
    # ----------------------------------------------

    else:

        regional_result = (

            await translate_to_regional(

                message=english_response,

                thread_id=thread_id,

                language=language

            )

        )


        final_response = (

            regional_result.get(

                "translation",

                english_response

            )

        )


        # ------------------------------------------
        # SAFETY FALLBACK
        # ------------------------------------------

        if (

            not final_response

            or

            not final_response.strip()

        ):

            print(
                "\nWARNING:"
            )

            print(
                "Empty translation received."
            )

            print(
                "Using English response."
            )


            final_response = english_response


    print("\nFINAL RESPONSE:")

    print(
        final_response
    )


    return (

        final_response,

        language

    )


# ==================================================
# HANDLE TEXT
# ==================================================

async def handle_text(

    update: Update,
    context: ContextTypes.DEFAULT_TYPE

):

    message = update.message.text


    # IMPORTANT:
    # This function is called only ONCE
    # for this incoming user message.

    thread_id = get_thread_id(
        update
    )


    try:

        print("\n================================")
        print("TEXT MESSAGE RECEIVED")
        print("================================")

        print(
            "Thread ID:",
            thread_id
        )


        print(
            "Message:",
            message
        )


        await update.message.reply_chat_action(

            action=ChatAction.TYPING

        )


        response, language = (

            await process_message(

                message=message,

                thread_id=thread_id

            )

        )


        await update.message.reply_text(

            response

        )


    except Exception as e:

        print("\nTEXT ERROR:\n")

        print(
            str(e)
        )


        await update.message.reply_text(

            "⚠️ Sorry, I could not process your message."

        )


# ==================================================
# HANDLE IMAGE
# ==================================================

async def handle_image(

    update: Update,
    context: ContextTypes.DEFAULT_TYPE

):

    # IMPORTANT:
    # get_thread_id() is called only once.

    thread_id = get_thread_id(
        update
    )


    # Highest quality photo

    photo = update.message.photo[-1]


    # Caption can be empty

    message = (

        update.message.caption

        or

        ""

    )


    try:

        print("\n================================")
        print("IMAGE RECEIVED")
        print("================================")

        print(
            "Thread ID:",
            thread_id
        )


        print(
            "Caption:",
            message
        )


        # ------------------------------------------
        # DOWNLOAD IMAGE
        # ------------------------------------------

        await update.message.reply_chat_action(

            action=ChatAction.UPLOAD_PHOTO

        )


        telegram_file = (

            await context.bot.get_file(

                photo.file_id

            )

        )


        file_bytes = (

            await telegram_file.download_as_bytearray()

        )


        # ------------------------------------------
        # UPLOAD IMAGE TO PARAKRAM
        # ------------------------------------------

        print(
            "\nUploading image..."
        )


        upload_result = (

            await upload_image(

                file_bytes=bytes(file_bytes),

                file_name="telegram_image.jpg",

                content_type="image/jpeg"

            )

        )


        if not upload_result.get(

            "success"

        ):

            raise Exception(

                "Image upload failed"

            )


        image_url = upload_result.get(

            "url"

        )


        if not image_url:

            raise Exception(

                "Image URL not returned"

            )


        print(
            "IMAGE URL:"
        )


        print(
            image_url
        )


        # ------------------------------------------
        # DEFAULT MESSAGE IF NO CAPTION
        # ------------------------------------------

        if not message.strip():

            message = (

                "The user has submitted an image "
                "as evidence. Analyze the image "
                "and help the user."

            )


        # ------------------------------------------
        # PROCESS MESSAGE
        # ------------------------------------------

        await update.message.reply_chat_action(

            action=ChatAction.TYPING

        )


        response, language = (

            await process_message(

                message=message,

                thread_id=thread_id,

                image_url=image_url,

                video_url=None

            )

        )


        await update.message.reply_text(

            response

        )


    except Exception as e:

        print("\nIMAGE ERROR:\n")

        print(
            str(e)
        )


        await update.message.reply_text(

            "⚠️ Sorry, I could not process this image."

        )


# ==================================================
# HANDLE VIDEO
# ==================================================

async def handle_video(

    update: Update,
    context: ContextTypes.DEFAULT_TYPE

):

    # IMPORTANT:
    # get_thread_id() is called only once.

    thread_id = get_thread_id(
        update
    )


    video = update.message.video


    # Caption can be empty

    message = (

        update.message.caption

        or

        ""

    )


    try:

        print("\n================================")
        print("VIDEO RECEIVED")
        print("================================")

        print(
            "Thread ID:",
            thread_id
        )


        print(
            "Caption:",
            message
        )


        # ------------------------------------------
        # DOWNLOAD VIDEO
        # ------------------------------------------

        await update.message.reply_chat_action(

            action=ChatAction.UPLOAD_VIDEO

        )


        telegram_file = (

            await context.bot.get_file(

                video.file_id

            )

        )


        file_bytes = (

            await telegram_file.download_as_bytearray()

        )


        content_type = (

            video.mime_type

            or

            "video/mp4"

        )


        # ------------------------------------------
        # UPLOAD VIDEO
        # ------------------------------------------

        print(
            "\nUploading video..."
        )


        upload_result = (

            await upload_video(

                file_bytes=bytes(file_bytes),

                file_name="telegram_video.mp4",

                content_type=content_type

            )

        )


        if not upload_result.get(

            "success"

        ):

            raise Exception(

                "Video upload failed"

            )


        video_url = upload_result.get(

            "url"

        )


        if not video_url:

            raise Exception(

                "Video URL not returned"

            )


        print(
            "VIDEO URL:"
        )


        print(
            video_url
        )


        # ------------------------------------------
        # DEFAULT MESSAGE IF NO CAPTION
        # ------------------------------------------

        if not message.strip():

            message = (

                "The user has submitted a video "
                "as evidence. Analyze the video "
                "and help the user."

            )


        # ------------------------------------------
        # PROCESS MESSAGE
        # ------------------------------------------

        await update.message.reply_chat_action(

            action=ChatAction.TYPING

        )


        response, language = (

            await process_message(

                message=message,

                thread_id=thread_id,

                image_url=None,

                video_url=video_url

            )

        )


        await update.message.reply_text(

            response

        )


    except Exception as e:

        print("\nVIDEO ERROR:\n")

        print(
            str(e)
        )


        await update.message.reply_text(

            "⚠️ Sorry, I could not process this video."

        )


# ==================================================
# HANDLE VOICE
# ==================================================

async def handle_voice(

    update: Update,
    context: ContextTypes.DEFAULT_TYPE

):

    # IMPORTANT:
    # get_thread_id() is called only once.

    thread_id = get_thread_id(
        update
    )


    voice = update.message.voice


    audio_path = None


    try:

        print("\n================================")
        print("VOICE MESSAGE RECEIVED")
        print("================================")


        print(
            "Thread ID:",
            thread_id
        )


        print(
            "Duration:",
            voice.duration
        )


        # ------------------------------------------
        # DOWNLOAD VOICE
        # ------------------------------------------

        await update.message.reply_chat_action(

            action=ChatAction.TYPING

        )


        telegram_file = (

            await context.bot.get_file(

                voice.file_id

            )

        )


        file_bytes = (

            await telegram_file.download_as_bytearray()

        )


        # ------------------------------------------
        # SPEECH → TEXT
        # ------------------------------------------

        print(
            "\nConverting speech to text..."
        )


        original_text, detected_audio_language = (

            await speech_to_text(

                bytes(file_bytes)

            )

        )


        # ------------------------------------------
        # PRINT DETECTED LANGUAGE
        # ------------------------------------------

        print(
            "\n================================"
        )

        print(
            "VOICE LANGUAGE DETECTED:"
        )

        print(
            detected_audio_language
        )

        print(
            "================================"
        )


        # ------------------------------------------
        # PRINT TRANSCRIPTION
        # ------------------------------------------

        print(
            "\nVOICE TRANSCRIPTION:"
        )


        print(
            original_text
        )


        # ------------------------------------------
        # EMPTY TRANSCRIPTION CHECK
        # ------------------------------------------

        if (

            not original_text

            or

            not original_text.strip()

        ):

            await update.message.reply_text(

                "⚠️ I could not understand "
                "the voice message."

            )

            return


        # ------------------------------------------
        # PROCESS COMPLETE PIPELINE
        # ------------------------------------------

        response, language = (

            await process_message(

                message=original_text,

                thread_id=thread_id

            )

        )


        # ------------------------------------------
        # SEND TEXT RESPONSE
        # ------------------------------------------

        await update.message.reply_text(

            response

        )


        # ------------------------------------------
        # TEXT → SPEECH
        # ------------------------------------------

        print(
            "\nGenerating voice response..."
        )


        await update.message.reply_chat_action(

            action=ChatAction.RECORD_VOICE

        )


        audio_path = (

            await text_to_speech(

                text=response,

                language=language

            )

        )


        # ------------------------------------------
        # SEND AUDIO RESPONSE
        # ------------------------------------------

        with open(

            audio_path,

            "rb"

        ) as audio:

            await update.message.reply_audio(

                audio=audio,

                title="Parakram Response"

            )


        print(
            "\nVOICE RESPONSE SENT SUCCESSFULLY"
        )


    except Exception as e:

        print(
            "\nVOICE PROCESSING ERROR:\n"
        )


        print(
            str(e)
        )


        await update.message.reply_text(

            "⚠️ Sorry, I could not process "
            "your voice message."

        )


    finally:

        # ------------------------------------------
        # CLEAN TEMP AUDIO FILE
        # ------------------------------------------

        if (

            audio_path

            and os.path.exists(audio_path)

        ):

            os.remove(
                audio_path
            )


# ==================================================
# MAIN
# ==================================================

def main():

    # ----------------------------------------------
    # BUILD TELEGRAM APPLICATION
    # ----------------------------------------------

    app = (

        ApplicationBuilder()

        .token(TOKEN)

        .build()

    )


    # ----------------------------------------------
    # START COMMAND
    # ----------------------------------------------

    app.add_handler(

        CommandHandler(

            "start",

            start

        )

    )


    # ----------------------------------------------
    # TEXT
    # ----------------------------------------------

    app.add_handler(

        MessageHandler(

            filters.TEXT

            & ~filters.COMMAND,

            handle_text

        )

    )


    # ----------------------------------------------
    # IMAGE
    # ----------------------------------------------

    app.add_handler(

        MessageHandler(

            filters.PHOTO,

            handle_image

        )

    )


    # ----------------------------------------------
    # VIDEO
    # ----------------------------------------------

    app.add_handler(

        MessageHandler(

            filters.VIDEO,

            handle_video

        )

    )


    # ----------------------------------------------
    # VOICE
    # ----------------------------------------------

    app.add_handler(

        MessageHandler(

            filters.VOICE,

            handle_voice

        )

    )


    print("\n================================")
    print("PARAKRAM TELEGRAM BOT RUNNING 🚀")
    print("================================")


    app.run_polling()


# ==================================================
# RUN
# ==================================================

if __name__ == "__main__":

    main()

