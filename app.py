import streamlit as st
import asyncio
import nest_asyncio
from services.llm_service import send_message_stream, send_message_with_file_stream
from services.file_processor import process_uploaded_file
from database.db import (
    init_db, create_conversation, get_all_conversations,
    add_message, get_messages, delete_conversation, get_token_stats
)
from services.moderation_service import moderate_input
from services.self_correction_service import validate_response, regenerate_response

nest_asyncio.apply()

# --- Oldal beállítások ---
st.set_page_config(
    page_title="📚 Tanulmányi Segítő",
    page_icon="📚",
    layout="wide"
)

# --- Async helper ---
def run_async(coro):
    loop = asyncio.get_event_loop()
    return loop.run_until_complete(coro)

# --- Inicializálás ---
run_async(init_db())

if "current_conversation_id" not in st.session_state:
    st.session_state.current_conversation_id = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# --- Sidebar ---
with st.sidebar:
    st.title("📚 Tanulmányi Segítő")
    st.markdown("---")

    # Új beszélgetés gomb
    if st.button("➕ Új beszélgetés", use_container_width=True):
        st.session_state.current_conversation_id = None
        st.session_state.messages = []
        st.rerun()

    st.markdown("---")

    # Hiperparaméterek
    st.subheader("⚙️ Hiperparaméterek")

    temperature = st.slider(
        "🌡️ Temperature",
        min_value=0.0, max_value=2.0, value=0.7, step=0.1,
        help="Magasabb = kreatívabb, alacsonyabb = precízebb"
    )
    top_p = st.slider(
        "🎯 Top P",
        min_value=0.0, max_value=1.0, value=0.9, step=0.05,
        help="A legvalószínűbb tokenek halmaza"
    )
    top_k = st.slider(
        "🔢 Top K",
        min_value=1, max_value=100, value=40, step=1,
        help="Top K token közül választ"
    )
    max_tokens = st.slider(
        "📏 Max tokenek",
        min_value=256, max_value=8192, value=2048, step=256,
        help="Válasz maximális hossza"
    )

    st.markdown("---")

    # Korábbi beszélgetések
    st.subheader("💬 Korábbi beszélgetések")
    conversations = run_async(get_all_conversations())

    for conv in conversations:
        col1, col2 = st.columns([4, 1])
        with col1:
            if st.button(f"📝 {conv['title'][:30]}...", key=f"conv_{conv['id']}", use_container_width=True):
                st.session_state.current_conversation_id = conv["id"]
                db_messages = run_async(get_messages(conv["id"]))
                st.session_state.messages = [
                    {"role": msg["role"], "content": msg["content"]}
                    for msg in db_messages
                ]
                st.rerun()
        with col2:
            if st.button("🗑️", key=f"del_{conv['id']}"):
                run_async(delete_conversation(conv["id"]))
                if st.session_state.current_conversation_id == conv["id"]:
                    st.session_state.current_conversation_id = None
                    st.session_state.messages = []
                st.rerun()

    # Token statisztikák
    st.markdown("---")
    st.subheader("📊 Token statisztikák")
    stats = run_async(get_token_stats())
    st.metric("Összes token", f"{stats['total_tokens']:,}")
    st.caption(f"Prompt: {stats['prompt_tokens']:,} | Válasz: {stats['completion_tokens']:,}")

# --- Fő chat terület ---
st.header("📚 Tanulmányi Segítő Chat")

# --- Fájl feltöltés ---
uploaded_file = st.file_uploader(
    "📎 Tölts fel fájlt (opcionális – PDF vagy kép):",
    type=["pdf", "png", "jpg", "jpeg", "webp"],
    help="Feltölthetsz egy dokumentumot vagy képet, és kérdezhetsz róla!"
)

if uploaded_file:
    st.success(f"✅ Feltöltve: `{uploaded_file.name}` – Most írj egy kérdést a fájlról!")

st.markdown("---")

# --- Üzenetek megjelenítése ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Chat input ---
if prompt := st.chat_input("Írj egy üzenetet..."):
    # Felhasználó üzenetének megjelenítése
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # Ha még nincs conversation, hozzunk létre egyet
    if st.session_state.current_conversation_id is None:
        st.session_state.current_conversation_id = run_async(create_conversation(prompt[:50]))

    # 🛡️ MODERÁCIÓ
    moderation_result = moderate_input(prompt)

    if not moderation_result["allowed"]:
        # Tiltott üzenet kezelése
        blocked_response = (
            f"⚠️ Ez az üzenet nem engedélyezett.\n\n"
            f"**Indok:** {moderation_result['reason']}\n\n"
            f"Kérlek, kérdezz tanulással kapcsolatos dolgokat! 📚"
        )
        with st.chat_message("assistant"):
            st.markdown(blocked_response)
        st.session_state.messages.append({"role": "assistant", "content": blocked_response})

        # Mentés az adatbázisba
        run_async(add_message(st.session_state.current_conversation_id, "user", prompt))
        run_async(add_message(st.session_state.current_conversation_id, "assistant", blocked_response))

    else:
        # ✅ Engedélyezett – LLM válasz (fájllal vagy anélkül)
        with st.chat_message("assistant"):
            message_placeholder = st.empty()
            full_response = ""

            gen_config = {
                "temperature": temperature,
                "top_p": top_p,
                "top_k": top_k,
                "max_output_tokens": max_tokens,
            }

            try:
                history = [
                    {"role": m["role"], "content": m["content"]}
                    for m in st.session_state.messages[:-1]
                ]

                # 📎 Fájl alapján döntjük el melyik függvényt hívjuk
                if uploaded_file is not None:
                    file_data = process_uploaded_file(uploaded_file)

                    if file_data["type"] == "unsupported":
                        full_response = "❌ Nem támogatott fájlformátum! Kérlek PDF-et vagy képet tölts fel."
                        message_placeholder.markdown(full_response)
                        prompt_tokens = 0
                        completion_tokens = 0
                        total_tokens = 0
                    else:
                        response = send_message_with_file_stream(history, prompt, file_data, gen_config)

                        for chunk in response:
                            if chunk.text:
                                full_response += chunk.text
                                message_placeholder.markdown(full_response + "▌")

                        message_placeholder.markdown(full_response)

                        prompt_tokens = chunk.usage_metadata.prompt_token_count if chunk.usage_metadata else 0
                        completion_tokens = chunk.usage_metadata.candidates_token_count if chunk.usage_metadata else 0
                        total_tokens = chunk.usage_metadata.total_token_count if chunk.usage_metadata else 0

                else:
                    # Normál streaming fájl nélkül
                    response = send_message_stream(history, prompt, gen_config)

                    for chunk in response:
                        if chunk.text:
                            full_response += chunk.text
                            message_placeholder.markdown(full_response + "▌")

                    message_placeholder.markdown(full_response)

                    prompt_tokens = chunk.usage_metadata.prompt_token_count if chunk.usage_metadata else 0
                    completion_tokens = chunk.usage_metadata.candidates_token_count if chunk.usage_metadata else 0
                    total_tokens = chunk.usage_metadata.total_token_count if chunk.usage_metadata else 0

                # 🔄 SELF-CORRECTION (csak ha volt érdemi válasz)
                if full_response and not full_response.startswith("❌"):
                    validation = validate_response(prompt, full_response)

                    if not validation["valid"]:
                        message_placeholder.markdown(full_response + "\n\n🔄 *Javítás folyamatban...*")

                        original_response = full_response
                        full_response = ""
                        regen_response = regenerate_response(
                            prompt, original_response,
                            validation["issues"], validation["suggestion"],
                            history, gen_config
                        )

                        for chunk in regen_response:
                            if chunk.text:
                                full_response += chunk.text
                                message_placeholder.markdown(full_response + "▌")

                        message_placeholder.markdown("✅ *Javított válasz:*\n\n" + full_response)

                        # Token számok frissítése
                        prompt_tokens += chunk.usage_metadata.prompt_token_count if chunk.usage_metadata else 0
                        completion_tokens = chunk.usage_metadata.candidates_token_count if chunk.usage_metadata else 0
                        total_tokens += chunk.usage_metadata.total_token_count if chunk.usage_metadata else 0

            except Exception as e:
                full_response = f"❌ Hiba történt: {str(e)}"
                message_placeholder.markdown(full_response)
                prompt_tokens = 0
                completion_tokens = 0
                total_tokens = 0

        st.session_state.messages.append({"role": "assistant", "content": full_response})

        # Mentés az adatbázisba
        run_async(add_message(
            st.session_state.current_conversation_id, "user", prompt,
            prompt_tokens=prompt_tokens, completion_tokens=0, total_tokens=prompt_tokens
        ))
        run_async(add_message(
            st.session_state.current_conversation_id, "assistant", full_response,
            prompt_tokens=0, completion_tokens=completion_tokens, total_tokens=completion_tokens
        ))