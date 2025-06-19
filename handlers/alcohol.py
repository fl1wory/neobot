from handlers.database import *
import datetime


async def db_add_alcohol_ingredients(message: Message, command: object):
    try:
        ing_name = str(command.args)
    except (TypeError, ValueError):
        await message.reply("Введіть назву інгредієнту правильно")
        return

    if await is_admin(message, message.from_user.id):
        con = sqlite3.connect("main.db")
        cur = con.cursor()
        # Використовуємо кортеж (ing_name,) замість (ing_name)
        cur.execute("SELECT title FROM alcohol_ingredients WHERE title = ?", (ing_name,))
        user_row = cur.fetchone()

        if user_row:
            await message.reply("Інгредієнт вже додано")
            con.close()
            return

        # Якщо ваша мета – додати новий інгредієнт, скористайтесь INSERT
        cur.execute("INSERT INTO alcohol_ingredients (title) VALUES(?)", (ing_name,))
        await message.reply("Інгредієнт додано")

        con.commit()
        con.close()

async def db_delete_alcohol_ingredient(message: Message, command: object):
    try:
        ing_name = str(command.args)
    except (TypeError, ValueError):
        await message.reply("Введіть назву інгредієнту правильно")
        return

    if await is_admin(message, message.from_user.id):
        con = sqlite3.connect("main.db")
        cur = con.cursor()
        # Перевіряємо, чи існує інгредієнт з такою назвою
        cur.execute("SELECT title FROM alcohol_ingredients WHERE title = ?", (ing_name,))
        row = cur.fetchone()
        if not row:
            await message.reply("Інгредієнт не знайдено")
            con.close()
            return

        # Видаляємо інгредієнт з бази
        cur.execute("DELETE FROM alcohol_ingredients WHERE title = ?", (ing_name,))
        con.commit()
        con.close()
        await message.reply("Інгредієнт видалено")
    else:
        await message.reply("У вас немає прав адміністратора")

def update_exposures():
    con = sqlite3.connect("main.db")
    cur = con.cursor()

    cur.execute("SELECT rowid, production_date FROM alcohol_inventory")
    rows = cur.fetchall()
    for rowid, production_date in rows:
        if production_date:
            prod_date = datetime.datetime.strptime(production_date, "%Y-%m-%d").date()
            days_passed = (datetime.date.today() - prod_date).days
            # один день = один місяць витримки
            exposure = days_passed
            value = exposure * 10  # оновлюємо ціну
            cur.execute("UPDATE alcohol_inventory SET exposure = ?, value = ? WHERE rowid = ?",
                        (exposure, value, rowid))

    con.commit()
    con.close()

async def add_recipe(message: Message, command: object):
    # 1) Перевіряємо, чи має користувач права адміністратора
    if not await is_admin(message, message.from_user.id):
        await message.reply("У вас немає прав для виконання цієї команди.")
        return

    # 2) Парсимо аргументи: очікуємо 6 частин через кому
    args = command.args or ""
    parts = [p.strip() for p in args.split(",")]
    if len(parts) != 7:
        await message.reply(
            "Неправильний формат! Використання:\n"
            "/add_recipe Назва, ing1, ing2, ing3, ing4, процес"
        )
        return

    title, ing1, ing2, ing3, ing4, process, time = parts

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
           AND time = ?
        """,
        (title, ing1, ing2, ing3, ing4, process, time)
    )
    if cur.fetchone():
        await message.reply("Такий рецепт уже існує в базі.")
        con.close()
        return

    # 4) Додаємо новий рецепт
    cur.execute(
        """
        INSERT INTO alcohol_base
          (title, ing1, ing2, ing3, ing4, process, time)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (title, ing1, ing2, ing3, ing4, process, time)
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
    cur.execute("SELECT title, exposure, value, is_cooked FROM alcohol_inventory WHERE id = ?", (user_id,))
    rows = cur.fetchall()
    con.close()

    if not rows:
        await message.answer("Ваш інвентар порожній.")
        return

    # Формування повідомлення з інвентарем
    inventory_list = "\n".join([f"Назва: {title}, Витримка: {exposure} днів, Ціна: {value}, Готовність: {is_cooked} " for title, exposure, value, is_cooked in rows])
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
        cur.execute("SELECT title, ing1, ing2, ing3, ing4, process, time FROM alcohol_base")
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
            "process": row[5],
            "time": row[6]
        }
        for row in rows
    ]
    return recipes