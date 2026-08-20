import httpx

from gateway.agent import (
    detect_language,
    regional_to_english,
    english_to_regional
)


BOT_API_URL = (
    "https://parakramuserreportchatbot-production.up.railway.app/chat"
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
    image_url: str | None = None,
    video_url: str | None = None
):

    # ----------------------------------------------
    # 1. Detect language
    # ----------------------------------------------

    language = detect_language(message)

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