import sqlite3
from aiogram.types import Message
from aiogram.filters import CommandObject

async def db_start():
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    await clear_db()
    cur.execute('''CREATE TABLE IF NOT EXISTS admins
                    (id text, username text)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS users
                    (id text, username text, account real, alcohol text, exposure real)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_base
                    (title text, ing1 text, ing2 text, ing3 text, ing4 text, process text)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_ingredients
                        (title text)''')

    con.commit()
    con.close()
    print("db created")

async def is_admin(message: Message, admin_id = None):
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute("SELECT id FROM admins WHERE id=?", (admin_id,))
    result = cur.fetchone()
    con.close()
    print(f"{message.from_user.full_name}, {message.from_user.id} is admin")
    return result is not None

async def is_user(message: Message, user_id = None):
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute("SELECT id FROM users WHERE id=?", (user_id,))
    result = cur.fetchone()
    con.close()
    print(f"{message.from_user.full_name}, {message.from_user.id} is user")
    return result is not None

async def clear_db():
    con = sqlite3.connect("main.db")
    cur = con.cursor()

    # Створюємо тимчасову таблицю з унікальними id
    cur.execute('''
        CREATE TEMPORARY TABLE admins_unique AS
        SELECT id, username FROM admins
        GROUP BY id
    ''')

    # Очищаємо таблицю admins
    cur.execute("DELETE FROM admins")

    # Вставляємо назад унікальні значення
    cur.execute('''
        INSERT INTO admins (id, username)
        SELECT id, username FROM admins_unique
    ''')

    con.commit()
    con.close()

##################################################Команди для користувачів##############################################
async def db_add_admin(message: Message):
    con = sqlite3.connect("main.db")
    cur = con.cursor()

    # Припускаємо, що аргументи містять id та full_name
    if message.reply_to_message != None:
        admin_id = message.reply_to_message.from_user.id
        admin_fullname = str(message.reply_to_message.from_user.full_name)

        # Тут можна викликати вашу функцію is_admin, але переконайтеся, що її сигнатура відповідає
        if not await is_admin(message, admin_id):
            cur.execute("INSERT INTO admins VALUES(?, ?)", (admin_id, admin_fullname))
            print(f'admin {message.reply_to_message.from_user.full_name}')


    con.commit()
    con.close()

async def db_add_user(message : Message):
    con = sqlite3.connect("main.db")
    cur = con.cursor()

    user_id = message.from_user.id
    username = message.from_user.full_name

    cur.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
    result = cur.fetchone()
    if result == None:
        cur.execute("INSERT INTO users VALUES(?, ?, ?)", (user_id, username, 0))
        await message.reply("Ти тепер користувач. Зіг Хайль!")
    else:
        await message.reply("Ти вже користувач")

    print(f'user {message.from_user.full_name}')

    con.commit()
    con.close()

async def addt(message: Message, command: object):
    # Перевірка, чи повідомлення є відповіддю на повідомлення іншого користувача
    if not message.reply_to_message:
        await message.reply("Напиши команду у відповідь на повідомлення")
        return

    # Спроба перетворити аргумент команди на число (float)
    try:
        amount = float(command.args)
    except (TypeError, ValueError):
        return

    if await is_admin(message, message.from_user.id):
        # Отримуємо id користувача, на повідомлення якого відповіли
        target_user_id = message.reply_to_message.from_user.id

        # Підключаємось до бази даних та перевіряємо, чи є користувач у таблиці users
        con = sqlite3.connect("main.db")
        cur = con.cursor()
        cur.execute("SELECT account FROM users WHERE id = ?", (target_user_id,))
        user_row = cur.fetchone()

        if not user_row:
            await message.reply("Користувача немає в базі даних.")
            con.close()
            return

        cur.execute("UPDATE users SET account = account + ? WHERE id = ?", (amount, target_user_id))
        await message.reply("Шекелі нараховано")
    # Якщо користувач існує, додаємо до його account суму amount

    con.commit()
    con.close()

async def delt(message: Message, command: object):
    # Перевірка, чи повідомлення є відповіддю на повідомлення іншого користувача
    if not message.reply_to_message:
        await message.reply("Будь ласка, відповідайте на повідомлення користувача, з якого потрібно відняти суму.")
        return

    # Спроба перетворити аргумент команди на число (float)
    try:
        amount = float(command.args)
    except (TypeError, ValueError):
        await message.reply("Будь ласка, вкажіть коректну суму (число).")
        return

    # Отримуємо id користувача, на повідомлення якого відповідаємо
    target_user_id = message.reply_to_message.from_user.id

    # Підключення до бази даних та перевірка наявності користувача у таблиці users
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute("SELECT account FROM users WHERE id = ?", (target_user_id,))
    user_row = cur.fetchone()

    if not user_row:
        await message.reply("Користувача немає в базі даних.")
        con.close()
        return

    # Віднімаємо суму amount від поточного значення account
    cur.execute("UPDATE users SET account = account - ? WHERE id = ?", (amount, target_user_id))
    con.commit()
    con.close()

    await message.reply("Сума успішно віднята від акаунту користувача.")

async def bal(message: Message):
    # Якщо команда викликана як відповідь на повідомлення, беремо дані того користувача,
    # інакше - використовуємо дані користувача, який написав команду.
    if message.reply_to_message:
        target_user = message.reply_to_message.from_user
        user_id = target_user.id
        name = target_user.full_name
    else:
        user_id = message.from_user.id
        name = message.from_user.full_name

    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute("SELECT account FROM users WHERE id = ?", (user_id,))
    row = cur.fetchone()
    con.close()

    if row is None:
        await message.reply(f"Користувач {name} не зареєстрований у базі даних.")
    else:
        balance = row[0]
        await message.reply(f"Баланс користувача {name}: {balance}")


async def topt(message: Message, command: object):
    # Спробуємо отримати аргумент команди як число
    try:
        top_n = int(command.args) if command.args and command.args.strip() != "" else None
    except ValueError:
        await message.reply("Будь ласка, вкажіть число як аргумент.")
        return

    con = sqlite3.connect("main.db")
    cur = con.cursor()

    # Вибираємо username та account, сортуємо за спаданням балансу
    if top_n is not None:
        cur.execute("SELECT username, account FROM users ORDER BY account DESC LIMIT ?", (top_n,))
    else:
        cur.execute("SELECT username, account FROM users ORDER BY account DESC")

    rows = cur.fetchall()
    con.close()

    if not rows:
        await message.reply("Немає користувачів у базі даних.")
        return

    # Формуємо рядки відповіді з топ списком користувачів
    response_lines = []
    for rank, (username, balance) in enumerate(rows, start=1):
        response_lines.append(f"{rank}. {username} - Баланс: {balance}")

    response_text = "\n".join(response_lines)
    await message.reply(response_text)
########################################################################################################################

