import aiosqlite
import asyncio
from datetime import datetime

DB_PATH = "chat_history.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                conversation_id INTEGER NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                attachment_type TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (conversation_id) REFERENCES conversations(id)
            )
        """)
        await db.commit()

async def create_conversation(title: str) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        cursor = await db.execute(
            "INSERT INTO conversations (title, created_at, updated_at) VALUES (?, ?, ?)",
            (title, now, now)
        )
        await db.commit()
        return cursor.lastrowid

async def get_all_conversations() -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM conversations ORDER BY updated_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def add_message(conversation_id: int, role: str, content: str,
                      prompt_tokens: int = 0, completion_tokens: int = 0,
                      total_tokens: int = 0, attachment_type: str = None):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        await db.execute(
            """INSERT INTO messages 
            (conversation_id, role, content, prompt_tokens, completion_tokens, total_tokens, attachment_type, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (conversation_id, role, content, prompt_tokens, completion_tokens, total_tokens, attachment_type, now)
        )
        await db.execute(
            "UPDATE conversations SET updated_at = ? WHERE id = ?",
            (now, conversation_id)
        )
        await db.commit()

async def get_messages(conversation_id: int) -> list:
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            "SELECT * FROM messages WHERE conversation_id = ? ORDER BY created_at ASC",
            (conversation_id,)
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]

async def delete_conversation(conversation_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("DELETE FROM messages WHERE conversation_id = ?", (conversation_id,))
        await db.execute("DELETE FROM conversations WHERE id = ?", (conversation_id,))
        await db.commit()

async def get_token_stats(conversation_id: int = None) -> dict:
    async with aiosqlite.connect(DB_PATH) as db:
        if conversation_id:
            cursor = await db.execute(
                """SELECT SUM(prompt_tokens) as total_prompt, 
                   SUM(completion_tokens) as total_completion,
                   SUM(total_tokens) as total 
                   FROM messages WHERE conversation_id = ?""",
                (conversation_id,)
            )
        else:
            cursor = await db.execute(
                """SELECT SUM(prompt_tokens) as total_prompt,
                   SUM(completion_tokens) as total_completion, 
                   SUM(total_tokens) as total 
                   FROM messages"""
            )
        row = await cursor.fetchone()
        return {
            "prompt_tokens": row[0] or 0,
            "completion_tokens": row[1] or 0,
            "total_tokens": row[2] or 0
        }