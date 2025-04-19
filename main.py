import asyncio
import logging
import sys
import sqlite3
import datetime
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, BotCommand, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram import Bot, Dispatcher, F
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from handlers import *  # Припускаємо, що ваші модулі database та alcohol знаходяться в handlers

# Bot token можна отримати через https://t.me/BotFather
TOKEN = "7713421550:AAG99SbCQsH4q9ke6eeEdiQGDWWGBMyDbj4"

dp = Dispatcher()
bot = None  # глобальна змінна для зберігання об'єкта Bot


def start_scheduler():
    scheduler = AsyncIOScheduler()

    # Обгортка для виконання синхронної функції
    def scheduled_update():
        print(f"[{datetime.datetime.now()}] Запуск оновлення витримки...")
        alcohol.update_exposures()
        print(f"[{datetime.datetime.now()}] Оновлення завершено.")

    # Запуск оновлення кожні 24 години. Можна також скористатись 'cron' для виконання, наприклад, опівночі.
    scheduler.add_job(scheduled_update, trigger='cron', hour=0, minute=0)
    # При бажанні, використовуйте trigger='cron' для фіксованого часу, наприклад:
    # scheduler.add_job(scheduled_update, trigger='cron', hour=0, minute=0)  # щодня опівночі

    scheduler.start()
    print("Планувальник APScheduler запущено.")

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Запустити бота"),
        BotCommand(command="/help", description="Отримати допомогу"),
        BotCommand(command="/add_admin", description="Додати адміністратора"),
        BotCommand(command="/user", description="Зареєструвати користувача"),
        BotCommand(command="/adds", description="Додати суму до рахунку"),
        BotCommand(command="/dels", description="Відняти суму від рахунку"),
        BotCommand(command="/bals", description="Показати баланс"),
        BotCommand(command="/tops", description="Показати топ рахунків"),
        BotCommand(command="/add_ingredient", description="Додати інгредієнт"),
        BotCommand(command="/del_ingredient", description="Видалити інгредієнт"),
        BotCommand(command="/add_recipe", description="Додати рецепт до alcohol_base"),
        BotCommand(command="/delete_recipe", description="Видалити рецепт із alcohol_base"),
        BotCommand(command="/add_process", description="Додати процес приготування"),
        BotCommand(command="/delete_process", description="Видалити процес приготування"),
        BotCommand(command="/brew", description="Варити алкоголь"),
        BotCommand(command="/inventory", description="Показати інвентар"),
        BotCommand(command="/processes", description="Показати процеси приготування"),
        BotCommand(command="/ingredients", description="Показати інгредієнти"),
        BotCommand(command="/recipes", description="Показати рецепти"),
    ]
    await bot.set_my_commands(commands)


async def main() -> None:
    global bot
    bot = Bot(token=TOKEN)
    await set_commands(bot)
    await database.db_start()
    start_scheduler()

    # Запуск опитування подій
    await dp.start_polling(bot)

@dp.message(CommandStart())
async def start(message: Message) -> None:
    await client.command_start_handler(message)

@dp.message(Command("add_admin"))
async def add_admin(message: Message) -> None:
    if await database.is_admin(message, message.from_user.id):
        await database.db_add_admin(message)
    else:
        await message.answer("Ти не маєш прав для виконання цієї дії")

@dp.message(Command("user"))
async def add_user(message: Message) -> None:
    await database.db_add_user(message)

@dp.message(Command("adds"))
async def addt(message: Message, command: object) -> None:
    await database.addt(message, command)

@dp.message(Command("dels"))
async def delt(message: Message, command: object) -> None:
    try:
        amount = float(command.args)
        await database.delt(message, amount)
    except (TypeError, ValueError):
        await message.reply("Будь ласка, вкажіть коректну суму (число).")
        return


@dp.message(Command("bals"))
async def bal(message: Message) -> None:
    await database.bal(message)

@dp.message(Command("tops"))
async def topt(message: Message, command: object) -> None:
    await database.topt(message, command)

@dp.message(Command("add_ingredient"))
async def add_ingredient(message: Message, command: object) -> None:
    print("початок")
    await alcohol.db_add_alcohol_ingredients(message, command)

@dp.message(Command("del_ingredient"))
async def del_ingredient(message: Message, command: object) -> None:
    await alcohol.db_delete_alcohol_ingredient(message, command)

@dp.message(Command("add_recipe"))
async def add_recipe(message: Message, command: object) -> None:
    await alcohol.add_recipe(message, command)

@dp.message(Command("delete_recipe"))
async def delete_recipe(message: Message, command: object):
    await alcohol.db_delete_recipe(message, command)

@dp.message(Command("add_process"))
async def add_process_handler(message: Message, command: object):
    await alcohol.db_add_process(message, command)

@dp.message(Command("delete_process"))
async def delete_process_handler(message: Message, command: object):
    await alcohol.db_delete_process(message, command)

@dp.message(Command("inventory"))
async def inventory_handler(message: Message):
    await alcohol.view_inventory(message)

@dp.message(Command('processes'))
async def processes_command(message: Message):
    processes = await alcohol.get_all_available_processes()
    if processes:
        text = "Доступні процеси приготування:\n\n"
        for proc in processes:
            text += f"Процес: {proc['title']}, Вартість: {proc['cost']}\n"
    else:
        text = "Немає доступних процесів."
    await message.reply(text)

@dp.message(Command('ingredients'))
async def ingredients_command(message: Message):
    ingredients = await alcohol.get_all_ingredients()
    if ingredients:
        text = "Наявні інгредієнти:\n" + "\n".join(f"- {ingr}" for ingr in ingredients)
    else:
        text = "Інгредієнтів не знайдено."
    await message.reply(text)

@dp.message(Command('recipes'))
async def recipes_command(message: Message):
    recipes = await alcohol.get_all_recipes()
    if recipes:
        text = "Наявні рецепти:\n\n"
        for rec in recipes:
            text += (
                f"Рецепт: {rec['title']}\n"
                f"Інгредієнти: {rec['ing1']}, {rec['ing2']}, {rec['ing3']}, {rec['ing4']}\n"
                f"Процес: {rec['process']}, Тривалість: {rec['time']} \n\n"

            )
    else:
        text = "Рецептів не знайдено."
    await message.reply(text)

# Глобальний словник для збереження сесій варки алкоголю
brew_sessions = {}  # ключ: user_id, значення: словник з даними сесії

# Допоміжні функції для роботи з базою даних
def get_alcohol_ingredients():
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute("SELECT title FROM alcohol_ingredients")
    rows = cur.fetchall()
    con.close()
    return [row[0] for row in rows]

def get_alcohol_processes():
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute("SELECT title, cost FROM alcohol_processes")
    rows = cur.fetchall()
    con.close()
    return rows  # повертає список кортежів (title, cost)

# Команда /brew <назва_алкоголю>
@dp.message(Command('brew'))
async def brew_command(message: Message):
    text = message.text or ""
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        await message.reply("Будь ласка, вкажіть назву алкоголю, наприклад: /brew Vodka")
        return
    alcohol_name = parts[1].strip()
    # Ініціалізуємо сесію для користувача
    brew_sessions[message.from_user.id] = {
        "alcohol_name": alcohol_name,
        "ingredients": [],
        "processes": []
    }
    # Створюємо початкову клавіатуру з кнопками "Створити" та "Закрити"
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="Створити", callback_data="brew_create"),
            InlineKeyboardButton(text="Закрити", callback_data="brew_close")
        ]
    ])
    await message.reply(f"Запуск процесу варки алкоголю: {alcohol_name}", reply_markup=keyboard)

# Обробка callback-запитів, пов’язаних з варкою алкоголю
@dp.callback_query(lambda c: c.data and c.data.startswith("brew_"))
async def process_brew(callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id

    # Перевірка, чи є користувач (якщо така функція визначена в database.is_user)
    if not await database.is_user(callback_query.message, user_id):
        await callback_query.answer("Користувач не знайдений. Зареєструйся командою /user", show_alert=True)
        return

    session = brew_sessions.get(user_id)
    if not session:
        await callback_query.answer("Сесія не знайдена. Будь ласка, запустіть процес командою /brew.", show_alert=True)
        return

    if data == "brew_close":
        # Скасування процесу
        await callback_query.message.edit_text("Процес варки скасовано.")
        brew_sessions.pop(user_id, None)
        await callback_query.answer()
        return

    elif data == "brew_create":
        # Відображення клавіатури з інгредієнтами
        ingredients = get_alcohol_ingredients()
        buttons = [[InlineKeyboardButton(text=ing, callback_data=f"brew_ing|{ing}")] for ing in ingredients]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback_query.message.edit_text("Вибери перший інгредієнт", reply_markup=keyboard)
        await callback_query.answer()
        return

    elif data.startswith("brew_ing|"):
        # Додаємо вибраний інгредієнт до сесії
        ing = data.split("|", 1)[1]
        if len(session["ingredients"]) < 4:
            session["ingredients"].append(ing)
        else:
            await callback_query.answer("Ви вже вибрали 4 інгредієнти", show_alert=True)
            return

        # Якщо інгредієнтів менше 4, запитуємо наступний інгредієнт
        if len(session["ingredients"]) < 4:
            ingredients = get_alcohol_ingredients()
            buttons = [[InlineKeyboardButton(text=ingr, callback_data=f"brew_ing|{ingr}")] for ingr in ingredients]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback_query.message.edit_text(
                f"Вибери інгредієнт {len(session['ingredients']) + 1}/4",
                reply_markup=keyboard
            )
        # Якщо вибрано 4 інгредієнти – переходимо до вибору процесу
        else:
            processes = get_alcohol_processes()
            # Формуємо кнопки. Якщо процес є "настоювання", то час не потрібен та callback включає час=0,
            # інакше callback без часу – буде запитувати введення.
            buttons = []
            for proc, cost in processes:
                if proc.lower() == "настоювання":
                    cb_data = f"brew_proc|{proc}|{cost}|0"
                else:
                    cb_data = f"brew_proc|{proc}|{cost}"
                buttons.append([InlineKeyboardButton(text=f"{proc} (-{cost})", callback_data=cb_data)])
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback_query.message.edit_text(
                "Усі інгредієнти вибрані. Тепер оберіть процес приготування:",
                reply_markup=keyboard
            )
        await callback_query.answer()
        return

    elif data.startswith("brew_proc|"):
        parts = data.split("|")
        proc = parts[1]
        try:
            base_cost = float(parts[2])
        except (IndexError, ValueError):
            await callback_query.answer("Некоректні дані процесу", show_alert=True)
            return

        # Якщо процес "настоювання", час не вводиться – встановлюємо time=0
        if proc.lower() == "настоювання":
            time_value = 0.0
            cost = base_cost  # встановлюється початкова вартість
            session["processes"].append({"process": proc, "cost": cost, "time": time_value})
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Завершити приготування", callback_data="brew_finish")]
            ])
            await callback_query.message.edit_text("Ви вибрали 4 інгредієнти. Завершіть приготування.",
                                                   reply_markup=keyboard)
            await callback_query.answer()
        else:
            # Якщо час не вказано в callback (тобто parts має довжину 3), запитуємо введення часу користувачем
            if len(parts) == 3:
                session["pending_process"] = {"process": proc, "base_cost": base_cost}
                await callback_query.message.edit_text("Введіть час процесу (у годинах):")
                await callback_query.answer()
                return
            else:
                try:
                    time_value = float(parts[3])
                except ValueError:
                    await callback_query.answer("Некоректна тривалість процесу", show_alert=True)
                    return
                # Якщо time_value == 0 і процес не є "настоювання", то cost = base_cost
                cost = base_cost * (time_value if time_value != 0 else 1)
                session["processes"].append({"process": proc, "cost": cost, "time": time_value})
                keyboard = InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Завершити приготування", callback_data="brew_finish")]
                ])
                await callback_query.message.edit_text("Ви вибрали 4 інгредієнти. Завершіть приготування.",
                                                       reply_markup=keyboard)
                await callback_query.answer()
        return

    elif data == "brew_finish":
        # Фінальний крок – завершення процесу
        total_cost = sum(item["cost"] for item in session["processes"])

        # Перевіряємо, чи існує користувач у таблиці users
        user_id_str = str(user_id)
        con = sqlite3.connect("main.db")
        cur = con.cursor()
        cur.execute("SELECT account FROM users WHERE id = ?", (user_id_str,))
        row = cur.fetchone()
        if not row:
            await callback_query.message.edit_text("Ви не користувач, зареєструйтесь командою /user")
            con.close()
            return
        else:
            current_account = row[0]

        if current_account - total_cost < 0:
            await callback_query.message.edit_text("Недостатньо коштів. Продукт не було виготовлено")
            con.close()
            return
        new_account = current_account - total_cost
        cur.execute("UPDATE users SET account = ? WHERE id = ?", (new_account, user_id_str))
        con.commit()
        con.close()

        # Формуємо дані для порівняння з таблицею alcohol_base
        ings = session["ingredients"]
        ings += [""] * (4 - len(ings))  # Заповнюємо, якщо вибрано менше 4 інгредієнтів
        processes_str = ", ".join([p["process"] for p in session["processes"]])
        alcohol_title = session["alcohol_name"]

        # Порівнюємо з таблицею alcohol_base (також враховуємо час процесу, збережений у рецепті)
        time_from_recipe = 0
        # Припустимо, що якщо серед обраних процесів є значення часу, то беремо суму
        for p in session["processes"]:
            time_from_recipe += p["time"]

        con = sqlite3.connect("main.db")
        cur = con.cursor()
        cur.execute("""SELECT * FROM alcohol_base 
                       WHERE title = ? 
                         AND ing1 = ? 
                         AND ing2 = ? 
                         AND ing3 = ? 
                         AND ing4 = ? 
                         AND process = ?
                         AND time = ?""",
                    (alcohol_title, ings[0], ings[1], ings[2], ings[3], processes_str, time_from_recipe))
        base_match = cur.fetchone()
        if base_match:
            # Продукт знайдено – записуємо час виготовлення та інші дані
            production_date = datetime.datetime.now()
            exposure = 0  # на момент створення
            value = exposure * 10  # приклад розрахунку вартості
            # Записуємо товар в інвентар із is_cooked = False
            cur.execute(
                "INSERT INTO alcohol_inventory (id, title, exposure, value, production_date, is_cooked) VALUES (?, ?, ?, ?, ?, ?)",
                (user_id, alcohol_title, exposure, value, production_date.isoformat(), False))
            inventory_message = "Продукт приготовано згідно рецепту, запис додано до інвентарю."
            con.commit()
            con.close()

            # Якщо час для процесу > 0, запускаємо відлік для оновлення is_cooked
            if time_from_recipe > 0:
                await asyncio.create_task(schedule_cooking_update(user_id, alcohol_title, time_from_recipe))
        else:
            inventory_message = "Процес приготування продукту порушено, запис в інвентар не здійснено."
            con.commit()
            con.close()

        result_text = (f"Приготування завершено!\n"
                       f"Алкоголь: {alcohol_title}\n"
                       f"Інгредієнти: {', '.join(session['ingredients'])}\n"
                       f"Процеси: {processes_str}\n"
                       f"Знято з рахунку: {total_cost}\n"
                       f"{inventory_message}")
        await callback_query.message.edit_text(result_text)
        brew_sessions.pop(user_id, None)
        await callback_query.answer()

    else:
        await callback_query.answer("Невідома дія", show_alert=True)

# Обробник повідомлень для введення часу процесу (якщо процес не «настоювання»)
@dp.message(lambda message: message.from_user.id in brew_sessions and "pending_process" in brew_sessions[message.from_user.id])
async def process_time_input(message: Message):
    user_id = message.from_user.id
    session = brew_sessions[user_id]
    try:
        time_value = float(message.text)
    except ValueError:
        await message.reply("Введіть числове значення часу (у годинах)!")
        return

    pending = session.pop("pending_process")
    proc = pending["process"]
    base_cost = pending["base_cost"]
    # Якщо time_value == 0, тоді cost = base_cost (тобто початкова вартість процесу)
    cost = base_cost * (time_value if time_value != 0 else 1)
    session["processes"].append({"process": proc, "cost": cost, "time": time_value})

    # Якщо 4 інгредієнти вже вибрано – переходимо до завершення
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Завершити приготування", callback_data="brew_finish")]
    ])
    await message.reply("Час процесу збережено. Натисніть 'Завершити приготування' для завершення.", reply_markup=keyboard)

# Асинхронна функція для оновлення значення is_cooked після спливу часу
async def schedule_cooking_update(user_id, alcohol_title, cooking_time_hours):
    """
    Функція чекає заданий час (у годинах, перетворюється в секунди)
    та після цього оновлює значення is_cooked на True для запису в інвентарі.
    """
    delay = cooking_time_hours * 3600  # переводимо години у секунди
    await asyncio.sleep(delay)
    con = sqlite3.connect("main.db")
    cur = con.cursor()
    cur.execute("UPDATE alcohol_inventory SET is_cooked = ? WHERE id = ? AND title = ?", (True, user_id, alcohol_title))
    con.commit()
    con.close()
    print(f"Оновлено is_cooked для {alcohol_title} користувача {user_id}")

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
