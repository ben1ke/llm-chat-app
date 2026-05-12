import base64
from google import genai
from google.genai import types
from config.settings import GEMINI_API_KEY, MODEL_NAME, DEFAULT_GENERATION_CONFIG
from config.system_prompts import STUDY_ASSISTANT_PROMPT

client = genai.Client(api_key=GEMINI_API_KEY)

def build_chat_history(messages: list) -> list:
    """Átalakítja az adatbázisból jövő üzeneteket Gemini formátumra."""
    history = []
    for msg in messages:
        role = "user" if msg["role"] == "user" else "model"
        history.append(
            types.Content(
                role=role,
                parts=[types.Part.from_text(text=msg["content"])]
            )
        )
    return history

def send_message_stream(messages: list, user_input: str, generation_config: dict = None):
    """Streaming válasz generálás."""
    config = generation_config or DEFAULT_GENERATION_CONFIG

    history = build_chat_history(messages)

    chat = client.chats.create(
        model=MODEL_NAME,
        history=history,
        config=types.GenerateContentConfig(
            system_instruction=STUDY_ASSISTANT_PROMPT,
            temperature=config.get("temperature", 0.7),
            top_p=config.get("top_p", 0.9),
            top_k=config.get("top_k", 40),
            max_output_tokens=config.get("max_output_tokens", 2048),
        )
    )

    response = chat.send_message_stream(user_input)
    return response

def send_message(messages: list, user_input: str, generation_config: dict = None):
    """Szinkron válasz generálás."""
    config = generation_config or DEFAULT_GENERATION_CONFIG

    history = build_chat_history(messages)

    chat = client.chats.create(
        model=MODEL_NAME,
        history=history,
        config=types.GenerateContentConfig(
            system_instruction=STUDY_ASSISTANT_PROMPT,
            temperature=config.get("temperature", 0.7),
            top_p=config.get("top_p", 0.9),
            top_k=config.get("top_k", 40),
            max_output_tokens=config.get("max_output_tokens", 2048),
        )
    )

    response = chat.send_message(user_input)
    return response

def send_message_with_file_stream(messages: list, user_input: str, 
                                   file_data: dict, generation_config: dict = None):
    """
    Fájlt (PDF szöveg vagy kép) is tartalmazó streaming válasz generálás.
    PDF esetén szövegként, kép esetén multimodálisan küldi el.
    """
    config = generation_config or DEFAULT_GENERATION_CONFIG

    history = build_chat_history(messages)

    chat = client.chats.create(
        model=MODEL_NAME,
        history=history,
        config=types.GenerateContentConfig(
            system_instruction=STUDY_ASSISTANT_PROMPT,
            temperature=config.get("temperature", 0.7),
            top_p=config.get("top_p", 0.9),
            top_k=config.get("top_k", 40),
            max_output_tokens=config.get("max_output_tokens", 2048),
        )
    )

    if file_data["type"] == "pdf":
        # PDF esetén a kinyert szöveget fűzzük a prompthoz
        combined_prompt = (
            f"{user_input}\n\n"
            f"📄 A feltöltött dokumentum tartalma:\n"
            f"{file_data['content'][:8000]}"
        )
        response = chat.send_message_stream(combined_prompt)

    elif file_data["type"] == "image":
        # Kép esetén multimodális üzenetet küldünk
        parts = [
            types.Part(
                inline_data=types.Blob(
                    mime_type=file_data["mime_type"],
                    data=base64.b64decode(file_data["content"])
                )
            ),
            types.Part.from_text(text=user_input)
        ]
        response = chat.send_message_stream(parts)

    else:
        # Fallback: sima szöveges küldés
        response = chat.send_message_stream(user_input)

    return response