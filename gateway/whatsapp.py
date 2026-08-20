import httpx
import os

from gateway.agent import (
    detect_language,
    regional_to_english,
    english_to_regional
)


BOT_API_URL = (
    "https://parakramuserreportchatbot-production.up.railway.app/chat"
)

UPLOAD_IMAGE_URL = (
    "https://parakramuserreportchatbot-production.up.railway.app/upload-image"
)

UPLOAD_VIDEO_URL = (
    "https://parakramuserreportchatbot-production.up.railway.app/upload-video"
)

TWILIO_ACCOUNT_SID = os.getenv(
    "TWILIO_ACCOUNT_SID"
)

TWILIO_AUTH_TOKEN = os.getenv(
    "TWILIO_AUTH_TOKEN"
)

# ==================================================
# CALL BOT API
# ==================================================

async def call_bot_api(
    message: str,
    thread_id: str,
    image_url: str | None = None,
    video_url: str | None = None
):

    payload = {
        "message": message,
        "thread_id": thread_id,
        "image_url": image_url,
        "video_url": video_url
    }

    async with httpx.AsyncClient() as client:

        response = await client.post(
            BOT_API_URL,
            json=payload,
            timeout=60.0
        )

        response.raise_for_status()

        return response.json()


# ==================================================
# PROCESS WHATSAPP MESSAGE
# ==================================================

async def process_whatsapp_message(

    message: str,

    user_id: str,

    media_url: str | None = None,

    media_content_type: str | None = None

):

        # ==============================================
    # DEFAULT MEDIA
    # ==============================================

    image_url = None

    video_url = None


    # ==============================================
    # PROCESS MEDIA
    # ==============================================

    if media_url and media_content_type:

        media_result = await process_media(

            media_url=media_url,

            media_content_type=media_content_type

        )

        image_url = media_result["image_url"]

        video_url = media_result["video_url"]

        print("\nMEDIA PROCESSED")

        print("Image URL:", image_url)

        print("Video URL:", video_url)

    # ----------------------------------------------
    # 1. Detect language
    # ----------------------------------------------

    # ==============================================
# LANGUAGE PROCESSING
# ==============================================

    if message.strip():

        language = detect_language(
            message
        )

        if language.lower() == "english":

            english_message = message

        else:

            english_message = regional_to_english(
                message
            )

    else:

        language = "English"

        english_message = ""

    print("\n================================")
    print("INCOMING WHATSAPP MESSAGE")
    print("================================")

    print("User:", user_id)
    print("Language:", language)
    print("Original:", message)

    # ----------------------------------------------
    # 2. Convert user message to English
    # ----------------------------------------------

    if language.lower() == "english":

        english_message = message

    else:

        english_message = regional_to_english(
            message
        )

    print("English:", english_message)

    # ----------------------------------------------
    # 3. Send English message to Bot API
    # ----------------------------------------------

    bot_result = await call_bot_api(

    message=english_message,

    thread_id=user_id,

    image_url=image_url,

    video_url=video_url

)

    # ----------------------------------------------
    # 4. Extract Bot Response
    # ----------------------------------------------

    if not bot_result.get("success"):

        raise Exception(
            "Bot API returned an unsuccessful response"
        )

    bot_response = bot_result.get(
        "response",
        "Sorry, I could not process your request."
    )

    print("Bot Response:", bot_response)

    # ----------------------------------------------
    # 5. Translate response back to user's language
    # ----------------------------------------------

    if language.lower() == "english":

        final_response = bot_response

    else:

        final_response = english_to_regional(

            message=bot_response,

            language=language

        )

    print("Final Response:", final_response)

    return {

        "success": True,

        "language": language,

        "english_message": english_message,

        "response": final_response

    }

# ==================================================
# PROCESS TWILIO MEDIA
# ==================================================

async def process_media(

    media_url: str,
    media_content_type: str

):

    image_url = None

    video_url = None

    # ----------------------------------------------
    # Download media from Twilio
    # ----------------------------------------------

    async with httpx.AsyncClient(
        auth=(
            TWILIO_ACCOUNT_SID,
            TWILIO_AUTH_TOKEN
        ),
        timeout=120.0
    ) as client:

        media_response = await client.get(
            media_url
        )

        media_response.raise_for_status()

        media_bytes = media_response.content

    # ----------------------------------------------
    # IMAGE
    # ----------------------------------------------

    if media_content_type.startswith("image/"):

        filename = "whatsapp_image"

        files = {

            "image": (
                filename,
                media_bytes,
                media_content_type
            )

        }

        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:

            response = await client.post(

                UPLOAD_IMAGE_URL,

                files=files

            )

            response.raise_for_status()

            data = response.json()

        if not data.get("success"):

            raise Exception(
                "Image upload failed"
            )

        image_url = data.get("url")

        return {

            "image_url": image_url,

            "video_url": None

        }

    # ----------------------------------------------
    # VIDEO
    # ----------------------------------------------

    elif media_content_type.startswith("video/"):

        filename = "whatsapp_video"

        files = {

            "video": (
                filename,
                media_bytes,
                media_content_type
            )

        }

        async with httpx.AsyncClient(
            timeout=120.0
        ) as client:

            response = await client.post(

                UPLOAD_VIDEO_URL,

                files=files

            )

            response.raise_for_status()

            data = response.json()

        if not data.get("success"):

            raise Exception(
                "Video upload failed"
            )

        video_url = data.get("url")

        return {

            "image_url": None,

            "video_url": video_url

        }

    # ----------------------------------------------
    # UNSUPPORTED MEDIA
    # ----------------------------------------------

    else:

        raise Exception(

            f"Unsupported media type: "
            f"{media_content_type}"

        )