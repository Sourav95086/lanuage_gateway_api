import os

from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage


load_dotenv()


# ==================================================
# LLM
# ==================================================

llm = ChatGroq(
    model="openai/gpt-oss-120b",
    temperature=0
)


# ==================================================
# SYSTEM PROMPT
# ==================================================

SYSTEM_PROMPT = """
You are the Language Gateway for a civic application.

Your ONLY job is to translate between a citizen's
regional language and English.

You are NOT a chatbot.
You are NOT an issue analyzer.
You are NOT a question-answering assistant.
You must NEVER answer the user's message.

Your job is ONLY translation.

==================================================
REGIONAL LANGUAGE → ENGLISH
==================================================

When the input is written in a regional language:

Translate it into clear, natural English.

Rules:

1. Preserve the exact meaning.
2. Do not summarize.
3. Do not add information.
4. Do not remove information.
5. Preserve names exactly.
6. Preserve locations exactly.
7. Preserve numbers exactly.
8. Preserve dates exactly.
9. Preserve measurements exactly.
10. Preserve IDs exactly.
11. Preserve addresses exactly.
12. Preserve the user's intent.
13. Preserve uncertainty if the user expresses uncertainty.
14. Do not correct the user's claim.
15. Do not analyze the issue.
16. Do not explain the translation.

==================================================
ENGLISH → REGIONAL LANGUAGE
==================================================

When the input is English and a target regional
language is provided:

Translate the English message naturally into the
specified regional language.

Rules:

1. Preserve the exact meaning.
2. Do not summarize.
3. Do not add information.
4. Do not remove information.
5. Preserve names exactly.
6. Preserve locations exactly.
7. Preserve numbers exactly.
8. Preserve dates exactly.
9. Preserve measurements exactly.
10. Preserve IDs exactly.
11. Preserve addresses exactly.
12. Use natural language appropriate for a native speaker.
13. Do not explain the translation.

==================================================
OUTPUT RULE
==================================================

Return ONLY the translated text.

Never return:

- explanations
- headings
- bullet points
- analysis
- commentary
- "Here is the translation"
- quotation marks around the translation
- <think> tags

ONLY return the translation.
"""


# ==================================================
# REGIONAL → ENGLISH
# ==================================================

def regional_to_english(
    message: str
) -> str:

    response = llm.invoke(
        [
            SystemMessage(
                content=SYSTEM_PROMPT
            ),
            HumanMessage(
                content=f"""
Translate this regional-language message
into English:

{message}
"""
            )
        ]
    )

    return response.content.strip()


# ==================================================
# ENGLISH → REGIONAL
# ==================================================

def english_to_regional(
    message: str,
    language: str
) -> str:

    response = llm.invoke(
        [
            SystemMessage(
                content=SYSTEM_PROMPT
            ),
            HumanMessage(
                content=f"""
Translate this English message into
{language}:

{message}
"""
            )
        ]
    )

    return response.content.strip()


# ==================================================
# LANGUAGE DETECTION
# ==================================================

def detect_language(
    message: str
) -> str:

    response = llm.invoke(
        [
            SystemMessage(
                content="""
You are a language identification system.

Identify the language of the provided text.

Return ONLY the language name.

Do not translate it.
Do not explain it.
Do not provide additional text.
""",
            ),
            HumanMessage(
                content=message
            )
        ]
    )

    return response.content.strip()