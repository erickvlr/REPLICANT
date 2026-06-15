import asyncio
from bot.client import build_bot
from database.sqlite import init_db
from config.settings import settings
from utils.console import print_banner, log_ok

async def main():
    print_banner()
    await init_db()
    log_ok("SQLite inicializado.")
    bot = build_bot()
    await bot.start(settings.discord_token)

if __name__ == "__main__":
    asyncio.run(main())
