import re
import json

from google import genai
from google.genai import types
from config.settings import GEMINI_API_KEY

client = genai.Client(api_key=GEMINI_API_KEY)

VALIDATION_PROMPT = """
Te egy válasz-ellenőrző AI vagy. A feladatod eldönteni, hogy egy tanulmányi segítő chatbot 
válasza megfelelő minőségű-e.

Ellenőrizd a következőket:
1. RELEVANCIA: A válasz kapcsolódik-e a kérdéshez?
2. PONTOSSÁG: Tartalmaz-e nyilvánvaló tévedést vagy félrevezető információt?
3. TELJESSEG: Elég részletes-e a válasz?
4. NYELV: Magyarul van-e (ha magyar volt a kérdés)?
5. HANGNEM: Segítőkész és tanulóbarát-e?

VÁLASZOD KIZÁRÓLAG az alábbi JSON formátumban add meg:
{"valid": true/false, "issues": "problémák listája ha van", "suggestion": "javítási javaslat ha kell"}

FONTOS:
- Ha a válasz alapvetően rendben van, MINDIG valid: true legyen.
- Csak KOMOLY problémáknál jelezz valid: false-t (pl. teljesen irreleváns, hibás info, nem magyar).
- Kisebb stilisztikai problémáknál is valid: true, de írd le az issues-ba.
"""

def _parse_json(text, fallback):
    """JSON kinyerése LLM válaszból (markdown, single quote kezelés)."""
    try:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            fixed = match.group(0).replace("'", '"').replace("True", "true").replace("False", "false")
            return json.loads(fixed)
    except Exception:
        pass
    return fallback

def validate_response(user_question: str, ai_response: str) -> dict:
    """
    Ellenőrzi az AI válaszát és visszaadja az eredményt.
    Returns: {"valid": bool, "issues": str, "suggestion": str}
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"KÉRDÉS: {user_question}\n\nVÁLASZ: {ai_response}",
            config=types.GenerateContentConfig(
                system_instruction=VALIDATION_PROMPT,
                temperature=0.1,
                max_output_tokens=200,
            )
        )

        result_text = response.text.strip()

        # JSON kinyerése ha markdown-ban jönne
        if "```" in result_text:
            result_text = result_text.split("```")[1]
            if result_text.startswith("json"):
                result_text = result_text[4:]
            result_text = result_text.strip()

        result = _parse_json(result_text, {"valid": True, "issues": "", "suggestion": ""})
        return {
            "valid": result.get("valid", True),
            "issues": result.get("issues", ""),
            "suggestion": result.get("suggestion", "")
        }

    except Exception as e:
        print(f"Validációs hiba: {e}")
        return {"valid": True, "issues": "", "suggestion": ""}

def regenerate_response(user_question: str, original_response: str, 
                         issues: str, suggestion: str, history: list, 
                         gen_config: dict):
    """
    Újragenerálja a választ a validáció alapján.
    Streaming generátort ad vissza.
    """
    enhanced_prompt = f"""{user_question}

FONTOS MEGJEGYZÉS: Az előző válaszod nem volt megfelelő.
Problémák: {issues}
Javaslat: {suggestion}
Kérlek, generálj egy javított, pontosabb választ!"""

    from services.llm_service import send_message_stream
    return send_message_stream(history, enhanced_prompt, gen_config)