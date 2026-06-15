import os
import asyncio
import aiosqlite
from config.settings import settings

db_lock = asyncio.Lock()

async def get_db():
    os.makedirs(os.path.dirname(settings.database_path), exist_ok=True)
    return await aiosqlite.connect(settings.database_path)

async def init_db():
    async with db_lock:
        db = await get_db()
        await db.executescript('''
        CREATE TABLE IF NOT EXISTS collaborators (
            user_id INTEGER PRIMARY KEY,
            level INTEGER NOT NULL DEFAULT 1
        );

        CREATE TABLE IF NOT EXISTS rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            triggers TEXT NOT NULL,
            reply TEXT NOT NULL,
            channels TEXT DEFAULT '',
            attachment_url TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT DEFAULT '',
            channel_id INTEGER,
            channel_name TEXT DEFAULT '',
            user_message TEXT NOT NULL,
            bot_reply TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS social_observations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id TEXT DEFAULT '',
            channel_id TEXT DEFAULT '',
            user_id TEXT DEFAULT '',
            username TEXT DEFAULT '',
            text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS social_profiles (
            scope_key TEXT PRIMARY KEY,
            messages INTEGER DEFAULT 0,
            slang TEXT DEFAULT '',
            emojis TEXT DEFAULT '',
            dominant_tone TEXT DEFAULT 'neutro',
            energy TEXT DEFAULT 'media',
            sample TEXT DEFAULT '',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS search_cache (
            query TEXT PRIMARY KEY,
            result_text TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS embed_templates (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            video_url TEXT DEFAULT '',
            image_url TEXT DEFAULT '',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS affection_profiles (
            user_id TEXT PRIMARY KEY,
            username TEXT DEFAULT '',
            interaction_count INTEGER DEFAULT 0,
            positive_count INTEGER DEFAULT 0,
            affection_score INTEGER DEFAULT 10,
            last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS factual_memory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            topic TEXT NOT NULL,
            content TEXT NOT NULL,
            tags TEXT DEFAULT '',
            created_by INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS ignored_channels (
            channel_id TEXT PRIMARY KEY,
            channel_name TEXT DEFAULT '',
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS registered_users (
            user_id TEXT PRIMARY KEY,
            username TEXT DEFAULT '',
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS character_rules (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            category TEXT DEFAULT 'comportamento',
            rule TEXT NOT NULL,
            added_by INTEGER,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        ''')
        await db.commit()

        # ── Migrations: adiciona colunas que podem faltar em DBs antigos ──
        migrations = [
            ("conversation_history", "username",     "TEXT DEFAULT ''"),
            ("conversation_history", "channel_name", "TEXT DEFAULT ''"),
        ]
        for table, col, col_def in migrations:
            try:
                await db.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
                await db.commit()
            except Exception:
                pass  # coluna já existe — ignorar

        await db.close()

async def execute(query: str, params: tuple = ()):
    async with db_lock:
        db = await get_db()
        await db.execute(query, params)
        await db.commit()
        await db.close()

async def fetchall(query: str, params: tuple = ()):
    db = await get_db()
    db.row_factory = aiosqlite.Row
    cur = await db.execute(query, params)
    rows = await cur.fetchall()
    await db.close()
    return rows

async def fetchone(query: str, params: tuple = ()):
    db = await get_db()
    db.row_factory = aiosqlite.Row
    cur = await db.execute(query, params)
    row = await cur.fetchone()
    await db.close()
    return row
