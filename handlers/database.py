import sqlite3
from aiogram.types import Message
from aiogram.filters import CommandObject
import asyncio

async def db_start():
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    await clear_db()
    cur.execute('''CREATE TABLE IF NOT EXISTS admins
                    (id text, username text)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS users (id text, username text, account real)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_base
                    (title text, ing1 text, ing2 text, ing3 text, ing4 text, process text)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_ingredients
                        (title text)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_processes
                            (title text, cost real)''')

    cur.execute('''CREATE TABLE IF NOT EXISTS alcohol_inventory
               (id text, title text, exposure real, value real, production_date text)''')

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
        con.commit()
        con.close()
    # Якщо користувач існує, додаємо до його account суму amount
    else:
        await message.reply("Іді нахуй хитрюга")


async def delt(message: Message, amount):
    # Перевірка, чи повідомлення є відповіддю на повідомлення іншого користувача
    if not message.reply_to_message:
        await message.reply("Будь ласка, відповідайте на повідомлення користувача, з якого потрібно відняти суму.")
        return

    # Спроба перетворити аргумент команди на число (float)

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

async def add_recipe(message: Message, command: object):
    # 1) Перевіряємо, чи має користувач права адміністратора
    if not await is_admin(message, message.from_user.id):
        await message.reply("У вас немає прав для виконання цієї команди.")
        return

    # 2) Парсимо аргументи: очікуємо 6 частин через кому
    args = command.args or ""
    parts = [p.strip() for p in args.split(",")]
    if len(parts) != 6:
        await message.reply(
            "Неправильний формат! Використання:\n"
            "/add_recipe Назва, ing1, ing2, ing3, ing4, процес"
        )
        return

    title, ing1, ing2, ing3, ing4, process = parts

    # 3) Перевіряємо, чи такий рецепт вже є в alcohol_base
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute(
        """
        SELECT 1 FROM alcohol_base
         WHERE title = ?
           AND ing1 = ?
           AND ing2 = ?
           AND ing3 = ?
           AND ing4 = ?
           AND process = ?
        """,
        (title, ing1, ing2, ing3, ing4, process)
    )
    if cur.fetchone():
        await message.reply("Такий рецепт уже існує в базі.")
        con.close()
        return

    # 4) Додаємо новий рецепт
    cur.execute(
        """
        INSERT INTO alcohol_base
          (title, ing1, ing2, ing3, ing4, process)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, ing1, ing2, ing3, ing4, process)
    )
    con.commit()
    con.close()

    await message.reply(f"Рецепт «{title}» успішно додано до alcohol_base.")

async def db_delete_recipe(message: Message, command: object):
    # 1) Перевіряємо права адміністратора
    if not await is_admin(message, message.from_user.id):
        await message.reply("У вас немає прав для виконання цієї команди.")
        return

    # 2) Парсимо аргумент — очікуємо назву рецепту
    title = (command.args or "").strip()
    if not title:
        await message.reply("Будь ласка, вкажіть назву рецепту для видалення, напр.: /delete_recipe Назва")
        return

    con = sqlite3.connect("main.db")
    cur = con.cursor()

    # 3) Перевіряємо, чи існує такий рецепт
    cur.execute(
        "SELECT 1 FROM alcohol_base WHERE title = ?",
        (title,)  # параметризований запит для безпеки та коректності :contentReference[oaicite:0]{index=0}
    )
    if not cur.fetchone():
        await message.reply(f"Рецепт «{title}» не знайдено в базі.")
        con.close()
        return

    # 4) Видаляємо рецепт із таблиці
    cur.execute(
        "DELETE FROM alcohol_base WHERE title = ?",
        (title,)  # використання DELETE для видалення одного рядка :contentReference[oaicite:1]{index=1}
    )
    con.commit()  # фіксуємо зміни в БД :contentReference[oaicite:2]{index=2}
    con.close()

    await message.reply(f"Рецепт «{title}» успішно видалено з бази.")

async def db_add_process(message: Message, command: object):
    # 1) Перевірка прав адміністратора
    if not await is_admin(message, message.from_user.id):
        await message.reply("У вас немає прав для виконання цієї команди.")
        return

    # 2) Парсимо аргументи: очікуємо "назва, вартість"
    args = (command.args or "").split(",")
    if len(args) != 2:
        await message.reply("Неправильний формат! Використання:\n"
                            "/add_process Назва, вартість")
        return
    title, cost_str = args[0].strip(), args[1].strip()

    # 3) Конвертуємо вартість у число
    try:
        cost = float(cost_str)
    except ValueError:
        await message.reply("Вартість має бути числом.")
        return

    con = sqlite3.connect("main.db")
    cur = con.cursor()
    # 4) Перевіряємо, чи такий процес уже існує
    cur.execute("SELECT 1 FROM alcohol_processes WHERE title = ?", (title,))  # :contentReference[oaicite:1]{index=1}
    if cur.fetchone():
        await message.reply(f"Процес «{title}» вже існує.")
        con.close()
        return

    # 5) Вставляємо новий рядок
    cur.execute(
        "INSERT INTO alcohol_processes (title, cost) VALUES (?, ?)",
        (title, cost)  # :contentReference[oaicite:2]{index=2}
    )
    con.commit()
    con.close()
    await message.reply(f"Процес «{title}» успішно додано.")

async def db_delete_process(message: Message, command: object):
    # 1) Перевірка прав адміністратора
    if not await is_admin(message, message.from_user.id):
        await message.reply("У вас немає прав для виконання цієї команди.")
        return

    # 2) Отримуємо назву процесу
    title = (command.args or "").strip()
    if not title:
        await message.reply("Будь ласка, вкажіть назву процесу для видалення:\n"
                            "/delete_process Назва")
        return

    con = sqlite3.connect("main.db")
    cur = con.cursor()
    # 3) Перевіряємо, чи процес існує
    cur.execute("SELECT 1 FROM alcohol_processes WHERE title = ?", (title,))  # :contentReference[oaicite:3]{index=3}
    if not cur.fetchone():
        await message.reply(f"Процес «{title}» не знайдено.")
        con.close()
        return

    # 4) Видаляємо рядок
    cur.execute("DELETE FROM alcohol_processes WHERE title = ?", (title,))  # :contentReference[oaicite:4]{index=4}
    con.commit()
    con.close()
    await message.reply(f"Процес «{title}» успішно видалено.")

async def view_inventory(message: Message):
    user_id = str(message.from_user.id)

    # Підключення до бази даних
    con = sqlite3.connect("main.db")
    cur = con.cursor()

    # Перевірка, чи існує користувач у таблиці users
    cur.execute("SELECT 1 FROM users WHERE id = ?", (user_id,))
    if not cur.fetchone():
        await message.answer("Ви не зареєстровані в системі. Будь ласка, скористайтеся командою /user для реєстрації.")
        con.close()
        return

    # Отримання записів інвентарю для користувача
    cur.execute("SELECT title, exposure, value FROM alcohol_inventory WHERE id = ?", (user_id,))
    rows = cur.fetchall()
    con.close()

    if not rows:
        await message.answer("Ваш інвентар порожній.")
        return

    # Формування повідомлення з інвентарем
    inventory_list = "\n".join([f"Назва: {title}, Витримка: {exposure} днів, Ціна: {value}" for title, exposure, value in rows])
    await message.answer(f"Ваш інвентар:\n{inventory_list}")

async def get_all_available_processes():
    """
    Повертає список усіх доступних процесів для приготування алкоголю.
    Кожен процес представлений у вигляді словника з ключами 'title' та 'cost'.
    """
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute("SELECT title, cost FROM alcohol_processes")
    rows = cur.fetchall()
    con.close()

    processes = [{"title": row[0], "cost": row[1]} for row in rows]
    return processes

async def get_all_ingredients():
    """
    Повертає список усіх інгредієнтів, доступних для приготування.
    Кожен інгредієнт представлений у вигляді рядка.
    """
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute("SELECT title FROM alcohol_ingredients")
    rows = cur.fetchall()
    con.close()

    ingredients = [row[0] for row in rows]
    return ingredients

async def get_all_recipes():
    """
    Повертає список усіх рецептів з таблиці alcohol_base.
    Кожен рецепт представлений у вигляді словника з ключами:
    'title', 'ing1', 'ing2', 'ing3', 'ing4', 'process'
    """
    loop = asyncio.get_running_loop()

    def db_query():
        con = sqlite3.connect("main.db")
        cur = con.cursor()
        cur.execute("SELECT title, ing1, ing2, ing3, ing4, process FROM alcohol_base")
        rows = cur.fetchall()
        con.close()
        return rows

    rows = await loop.run_in_executor(None, db_query)
    recipes = [
        {
            "title": row[0],
            "ing1": row[1],
            "ing2": row[2],
            "ing3": row[3],
            "ing4": row[4],
            "process": row[5]
        }
        for row in rows
    ]
    return recipes