
import asyncio
from handlers.database import run_migration

async def main():
    """Основна функція для запуску міграції."""
    print("Starting database migration process...")
    await run_migration()
    print("Migration process finished.")

if __name__ == "__main__":
    # Запускаємо асинхронну функцію main
    asyncio.run(main())