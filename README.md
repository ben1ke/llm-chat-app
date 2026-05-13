# 📚 Tanulmányi Segítő Chat

Egy mesterséges intelligencia alapú tanulmányi segítő chatbot, amely a Google Gemini API-t használja. Az alkalmazás Streamlit webes felületen fut, és képes szöveges beszélgetésre, PDF/kép feldolgozásra, moderációra és önjavító mechanizmusra.

> **Neptun kód:** U26PRR  
> **Készítette:** Kovács Bence  
> **Kurzus:** LLM és GPT modellek – 2025/26 tavasz

---

## 📑 Tartalomjegyzék

- [Funkciók](#-funkciók)
- [Architektúra](#-architektúra)
- [Projekt struktúra](#-projekt-struktúra)
- [Telepítés](#️-telepítés)
- [Futtatás](#-futtatás)
- [Használat](#-használat)
- [Technológiák](#-technológiák)

---

## ✨ Funkciók

| Funkció | Leírás |
|---|---|
| 💬 **Chat** | Valós idejű, streaming alapú beszélgetés a Gemini LLM-mel |
| 📜 **Chat history** | Korábbi beszélgetések mentése és visszatöltése SQLite adatbázisból |
| 🔢 **Token tracking** | Prompt, válasz és összesített token használat nyomon követése |
| ⚙️ **Hiperparaméterek** | Temperature, Top P, Top K és Max tokenek dinamikus állítása a felületen |
| 🛡️ **LLM-alapú moderáció** | Válaszgenerálás előtt egy külön LLM hívás ellenőrzi, hogy a prompt nem próbálja-e támadni a rendszert |
| 🔄 **Önjavító mechanizmus** | A háttérben egy másik LLM hívás ellenőrzi a válasz relevanciáját, és szükség esetén újragenerálja |
| 📎 **Fájl feltöltés** | PDF dokumentumok és képek (PNG, JPG, WEBP) feltöltése és elemzése |
| 🎓 **System prompt** | Részletes, jól strukturált system prompt a tanulmányi asszisztens szerephez |

---

## 🏗️ Architektúra

Az alkalmazás moduláris felépítésű. Az egyes komponensek jól elkülönülnek:

```
┌─────────────────────────────────────────────────┐
│                  Streamlit UI                   │
│                   (app.py)                      │
├────────┬────────┬───────────┬───────────────────┤
│ LLM    │Modera- │  Self-    │  File             │
│Service │tion    │Correction │  Processor        │
│        │Service │ Service   │                   │
├────────┴────────┴───────────┴───────────────────┤
│              Google Gemini API                  │
├─────────────────────────────────────────────────┤
│            SQLite Database (aiosqlite)          │
└─────────────────────────────────────────────────┘
```

### Adatfolyam

1. **Felhasználó** → üzenetet ír (opcionálisan fájlt csatol)
2. **Moderáció** → LLM ellenőrzi a prompt biztonságát
3. **LLM Service** → Gemini streaming válasz generálás (fájllal vagy anélkül)
4. **Self-Correction** → LLM ellenőrzi a válasz relevanciáját
5. **Database** → Üzenetek és token statisztikák mentése
6. **UI** → Válasz megjelenítése valós időben

---

## 📂 Projekt struktúra

```
llm-chat-app/
├── app.py                              # Fő Streamlit alkalmazás
├── config/
│   ├── settings.py                     # API kulcsok, modell konfiguráció
│   └── system_prompts.py              # System prompt definíciók
├── database/
│   └── db.py                          # SQLite adatbázis kezelés (async)
├── services/
│   ├── llm_service.py                 # Gemini API kommunikáció (streaming)
│   ├── moderation_service.py          # Input moderáció
│   ├── self_correction_service.py     # Válasz validálás és újragenerálás
│   └── file_processor.py             # PDF és kép feldolgozás
├── docs/
│   └── ...                            # UML diagramok, architektúra dokumentáció
├── requirements.txt                   # Python függőségek
└── README.md                          # Ez a fájl
```

---

## ⚙️ Telepítés

### 1. Repó klónozása

```bash
git clone https://github.com/ben1ke/llm-chat-app.git
cd llm-chat-app
```

### 2. Virtuális környezet létrehozása

```bash
python -m venv .venv
source .venv/bin/activate        # macOS / Linux
# .venv\Scripts\activate         # Windows
```

### 3. Függőségek telepítése

```bash
pip install -r requirements.txt
```

### 4. Környezeti változók beállítása

Hozz létre egy `.env` fájlt a projekt gyökerében:

```env
GEMINI_API_KEY=ide_jön_a_te_gemini_api_kulcsod
```

> 🔑 API kulcsot a [Google AI Studio](https://aistudio.google.com/app/apikey) oldalon tudsz generálni.

---

## 🚀 Futtatás

```bash
streamlit run app.py
```

Az alkalmazás alapértelmezetten a `http://localhost:8501` címen érhető el.

---

## 📖 Használat

### 💬 Alap csevegés

Egyszerűen írd be a kérdésedet a chat mezőbe. A válasz valós időben, streaming módban jelenik meg.

### ⚙️ Hiperparaméterek állítása

A bal oldali sávban (sidebar) állíthatod:

- **Temperature** – Magasabb = kreatívabb, alacsonyabb = precízebb
- **Top P** – A legvalószínűbb tokenek halmazának mérete
- **Top K** – Hány token közül választ a modell
- **Max tokenek** – A válasz maximális hossza

### 📎 Fájl feltöltés

1. A sidebarban töltsd fel a PDF-et vagy képet
2. Írd be a kérdésedet a chatben (pl. *„Foglald össze!"* vagy *„Mit látsz a képen?"*)
3. A modell a fájl tartalma alapján válaszol

### 💾 Beszélgetések kezelése

- **➕ Új beszélgetés** – Új chat indítása
- **📝 Korábbi beszélgetés** – Kattints rá a betöltéshez
- **🗑️ Törlés** – Beszélgetés eltávolítása

### 📊 Token statisztikák

A sidebar alján láthatod az összesített token felhasználást.

---

## 🛠️ Technológiák

| Technológia | Verzió | Felhasználás |
|---|---|---|
| [Python](https://python.org) | 3.12+ | Programnyelv |
| [Streamlit](https://streamlit.io) | latest | Webes felület |
| [Google Gemini API](https://ai.google.dev) | latest | Nagy nyelvi modell |
| [aiosqlite](https://github.com/omnilib/aiosqlite) | latest | Aszinkron SQLite |
| [PyMuPDF](https://pymupdf.readthedocs.io) | latest | PDF feldolgozás |
| [nest-asyncio](https://github.com/erdewit/nest_asyncio) | latest | Async kompatibilitás |

---
