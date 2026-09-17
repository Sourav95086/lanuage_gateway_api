
import os
import asyncio

import httpx

from dotenv import load_dotenv

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
# LANGUAGE GATEWAY
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
# VOICE AGENT
# ==================================================

VOICE_AGENT_URL = os.getenv(
    "VOICE_AGENT_URL",
    "http://127.0.0.1:8000"
).rstrip("/")

VOICE_TRANSCRIBE_URL = f"{VOICE_AGENT_URL}/voice/transcribe"
VOICE_SYNTHESIZE_URL = f"{VOICE_AGENT_URL}/voice/synthesize"


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
# GET THREAD ID
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
# VOICE AGENT → SPEECH TO TEXT
# ==================================================

async def speech_to_text(
    file_bytes: bytes,
    file_name: str = "telegram_voice.ogg"
) -> tuple[str, str]:
    """
    Send Telegram voice/audio bytes to the dedicated Voice Agent.

    Returns:
        (transcription, detected_language)
    """

    if not file_bytes:
        raise Exception("Voice file is empty.")

    files = {
        "audio": (
            file_name,
            file_bytes,
            "audio/ogg"
        )
    }

    print("\n================================")
    print("SENDING AUDIO TO VOICE AGENT")
    print("================================")
    print("URL:", VOICE_TRANSCRIBE_URL)
    print("Filename:", file_name)
    print("Size:", len(file_bytes), "bytes")

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                VOICE_TRANSCRIBE_URL,
                files=files
            )

        print("VOICE AGENT STATUS:", response.status_code)
        print("VOICE AGENT RESPONSE:", response.text)

        response.raise_for_status()
        result = response.json()

        if not result.get("success"):
            raise Exception(
                result.get("detail", "Voice transcription failed.")
            )

        text = (result.get("text") or "").strip()
        language = result.get("language", "English")

        if not text:
            raise Exception("Voice Agent returned an empty transcription.")

        return text, language

    except httpx.RequestError as e:
        raise Exception(
            f"Could not connect to Voice Agent at {VOICE_AGENT_URL}: {e}"
        )
    except httpx.HTTPStatusError as e:
        detail = e.response.text if e.response is not None else str(e)
        raise Exception(
            f"Voice Agent transcription failed: {detail}"
        )


# ==================================================
# LANGUAGE GATEWAY
# REGIONAL → ENGLISH
# ==================================================# ==================================================
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
# VOICE AGENT → TEXT TO SPEECH
# ==================================================

async def text_to_speech(
    text: str,
    language: str
) -> str:
    """
    Send text and language to the dedicated Voice Agent and
    save the returned MP3 locally so Telegram can send it.
    """

    if not text or not text.strip():
        raise Exception("TTS text cannot be empty.")

    data = {
        "text": text,
        "language": language
    }

    print("\n================================")
    print("SENDING TEXT TO VOICE AGENT")
    print("================================")
    print("URL:", VOICE_SYNTHESIZE_URL)
    print("Language:", language)

    try:
        async with httpx.AsyncClient(timeout=180.0) as client:
            response = await client.post(
                VOICE_SYNTHESIZE_URL,
                data=data
            )

        print("VOICE TTS STATUS:", response.status_code)

        response.raise_for_status()

        if not response.content:
            raise Exception("Voice Agent returned empty audio.")

        with open(
            "telegram_voice_response.mp3",
            "wb"
        ) as audio_file:
            audio_file.write(response.content)

        return os.path.abspath("telegram_voice_response.mp3")

    except httpx.RequestError as e:
        raise Exception(
            f"Could not connect to Voice Agent at {VOICE_AGENT_URL}: {e}"
        )
    except httpx.HTTPStatusError as e:
        detail = e.response.text if e.response is not None else str(e)
        raise Exception(
            f"Voice Agent TTS failed: {detail}"
        )


# ==================================================
# COMPLETE MESSAGE PIPELINE
# ==================================================# ==================================================
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

                bytes(file_bytes),
                "telegram_voice.ogg"

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

