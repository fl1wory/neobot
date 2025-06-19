import sqlite3
from contextlib import contextmanager

from aiogram.filters import CommandObject
from werkzeug.security import generate_password_hash


DB_NAME = "main.db"


@contextmanager
def db_connection():
    """Контекстний менеджер для безпечного з'єднання з базою даних."""
    con = sqlite3.connect(DB_NAME)
    try:
        cur = con.cursor()
        yield cur
        con.commit()
    finally:
        con.close()


async def run_migration():
    """
    Виконує міграцію бази даних.
    Перевіряє, чи існує колонка 'password' в таблиці 'admins'.
    Якщо ні, додає її та встановлює пароль за замовчуванням для всіх існуючих адмінів.
    """
    print("Checking database schema...")
    with db_connection() as cur:
        # Отримуємо інформацію про колонки в таблиці admins
        cur.execute("PRAGMA table_info(admins)")
        columns = [row[1] for row in cur.fetchall()]

        # Перевіряємо, чи існує колонка 'password'
        if 'password' not in columns:
            print("!!! Running database migration: Adding 'password' column to 'admins' table.")

            # 1. Додаємо нову колонку. Вона може бути NULL на цьому етапі.
            cur.execute("ALTER TABLE admins ADD COLUMN password TEXT")

            # 2. Встановлюємо пароль за замовчуванням для ВСІХ існуючих адміністраторів
            default_password = 'admin123'
            hashed_password = generate_password_hash(default_password)

            cur.execute("UPDATE admins SET password = ?", (hashed_password,))

            print("=" * 50)
            print("!!! Міграцію успішно завершено !!!")
            print(f"    Для всіх існуючих адміністраторів встановлено пароль за замовчуванням.")
            print(f"    Пароль: {default_password}")
            print("=" * 50)
        else:
            print("Database schema is up to date.")


async def db_start():
    """
    Ініціалізує базу даних, створюючи всі необхідні таблиці.
    Спочатку запускає міграцію для оновлення схеми.
    """
    # Спочатку запускаємо міграцію, щоб переконатися, що схема актуальна
    await run_migration()

    with db_connection() as cur:
        # Код для створення таблиць залишається на випадок, якщо БД не існує взагалі
        cur.execute('''CREATE TABLE IF NOT EXISTS admins
                        (id TEXT PRIMARY KEY, 
                         username TEXT, 
                         password TEXT)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS users (id TEXT PRIMARY KEY, username TEXT, account REAL)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_base
                        (title TEXT, ing1 TEXT, ing2 TEXT, ing3 TEXT, ing4 TEXT, process TEXT, time REAL)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_ingredients
                        (title TEXT PRIMARY KEY)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_processes
                            (title TEXT PRIMARY KEY, cost REAL)''')

        cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_inventory
                   (id TEXT, product_id INTEGER, title TEXT, exposure REAL, value REAL, production_date TEXT, is_cooked BOOLEAN,
                   PRIMARY KEY (id, product_id))''')

    print("Database initialized or checked successfully.")


# ... (решта коду файлу database.py, такий як is_admin, is_user і т.д., залишається без змін) ...
# ВАЖЛИВО: переконайтеся, що решта функцій з вашого оригінального файлу тут присутня
# Я залишу тут ті, що ми обговорювали.

from aiogram.types import Message


async def is_admin(message: Message, admin_id=None) -> bool:
    """Перевіряє, чи є користувач адміністратором."""
    # Ця функція залишається як є, вона не використовується в веб-логіні
    with db_connection() as cur:
        cur.execute("SELECT id FROM admins WHERE id=?", (admin_id,))
        result = cur.fetchone()
    return result is not None

async def is_user(message: Message, user_id=None) -> bool:
    """
    Перевіряє, чи є користувач зареєстрованим.

    :param message: Об'єкт повідомлення aiogram.
    :param user_id: ID користувача для перевірки.
    :return: True, якщо користувач зареєстрований, інакше False.
    """
    with db_connection() as cur:
        cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
        result = cur.fetchone()
    if result:
        print(f"User check: {message.from_user.full_name} ({message.from_user.id}) is a user.")
    return result is not None

async def clear_db():
    """
    Видаляє дублікати адміністраторів з таблиці `admins`.
    Це тимчасове рішення, краще використовувати `PRIMARY KEY` на `id`.
    """
    with db_connection() as cur:
        # Цей запит залишає тільки унікальні ID, видаляючи всі дублікати
        cur.execute('''
            DELETE FROM admins
            WHERE rowid NOT IN (
                SELECT MIN(rowid)
                FROM admins
                GROUP BY id
            )
        ''')
    print("Duplicate admins cleared.")

async def db_add_admin(message: Message):
    """
    Додає нового адміністратора, якщо він ще не є адміном.
    Працює при відповіді на повідомлення іншого користувача.
    """
    if message.reply_to_message:
        admin_id = str(message.reply_to_message.from_user.id)
        admin_fullname = str(message.reply_to_message.from_user.full_name)

        if not await is_admin(message, admin_id):
            with db_connection() as cur:
                # Використовуємо INSERT OR IGNORE для уникнення помилок з дублікатами
                cur.execute("INSERT OR IGNORE INTO admins (id, username) VALUES (?, ?)", (admin_id, admin_fullname))
            await message.reply(f"Admin {admin_fullname} added.")
            print(f"Admin {admin_fullname} added.")

async def db_add_user(message: Message):
    """
    Реєструє нового користувача або повідомляє, що він вже зареєстрований.
    """
    user_id = str(message.from_user.id)
    username = message.from_user.full_name

    with db_connection() as cur:
        cur.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
        if cur.fetchone() is None:
            cur.execute("INSERT INTO users (id, username, account) VALUES (?, ?, ?)", (user_id, username, 0))
            await message.reply("Ти тепер користувач. Зіг Хайль!")
            print(f'User {username} registered.')
        else:
            await message.reply("Ти вже користувач.")

async def addt(message: Message, command: CommandObject):
    """
    Додає кошти на рахунок користувача (тільки для адмінів).
    Працює при відповіді на повідомлення.
    """
    if not message.reply_to_message:
        await message.reply("Напиши команду у відповідь на повідомлення.")
        return

    try:
        amount = float(command.args)
    except (TypeError, ValueError):
        await message.reply("Неправильний формат суми. Введіть число.")
        return

    if await is_admin(message, message.from_user.id):
        target_user_id = str(message.reply_to_message.from_user.id)
        with db_connection() as cur:
            cur.execute("UPDATE users SET account = account + ? WHERE id = ?", (amount, target_user_id))
        await message.reply("Шекелі нараховано.")
    else:
        await message.reply("У вас немає прав для виконання цієї дії.")

async def delt(message: Message, amount: float):
    """
    Знімає кошти з рахунку користувача (тільки для адмінів).
    Працює при відповіді на повідомлення.
    """
    if not message.reply_to_message:
        await message.reply("Будь ласка, відповідайте на повідомлення користувача.")
        return

    target_user_id = str(message.reply_to_message.from_user.id)

    if await is_admin(message, message.from_user.id):
        with db_connection() as cur:
            cur.execute("UPDATE users SET account = account - ? WHERE id = ?", (amount, target_user_id))
        await message.reply("Сума успішно віднята.")
    else:
        await message.reply("У вас немає прав для виконання цієї дії.")

async def bal(message: Message):
    """
    Показує баланс користувача (або того, на чиє повідомлення відповіли).
    """
    target_user = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    user_id = str(target_user.id)
    name = target_user.full_name

    with db_connection() as cur:
        cur.execute("SELECT account FROM users WHERE id = ?", (user_id,))
        row = cur.fetchone()

    if row is None:
        await message.reply(f"Користувач {name} не зареєстрований.")
    else:
        balance = row[0]
        await message.reply(f"Баланс користувача {name}: {balance:.2f}")

async def topt(message: Message, command: CommandObject):
    """
    Показує топ користувачів за балансом.
    Приймає опціональний аргумент - кількість користувачів для показу.
    """
    try:
        top_n = int(command.args) if command.args and command.args.strip() else None
    except ValueError:
        await message.reply("Будь ласка, вкажіть число як аргумент.")
        return

    with db_connection() as cur:
        if top_n is not None:
            cur.execute("SELECT username, account FROM users ORDER BY account DESC LIMIT ?", (top_n,))
        else:
            cur.execute("SELECT username, account FROM users ORDER BY account DESC")
        rows = cur.fetchall()

    if not rows:
        await message.reply("Немає користувачів у базі даних.")
        return

    response_lines = [f"{rank}. {username} - Баланс: {balance:.2f}" for rank, (username, balance) in enumerate(rows, start=1)]
    await message.reply("\n".join(response_lines))