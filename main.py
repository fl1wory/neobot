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
                f"Процес: {rec['process']}\n\n"
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
    alcohol_name = parts[1].strip().lower()
    # Ініціалізуємо сесію для користувача
    brew_sessions[message.from_user.id] = {
        "alcohol_name": alcohol_name,
        "ingredients": [],
        "processes": []
    }
    # Створюємо початкову клавіатуру з кнопками "Створити" та "Закрити"
    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="Створити", callback_data="brew_create"),
                InlineKeyboardButton(text="Закрити", callback_data="brew_close")
            ]
        ]
    )
    await message.reply(f"Запуск процесу варки алкоголю: {alcohol_name}", reply_markup=keyboard)


# Обробка callback-запитів, пов’язаних з варкою алкоголю
@dp.callback_query(F.data.startswith("brew_"))
async def process_brew(callback_query: CallbackQuery):
    data = callback_query.data
    user_id = callback_query.from_user.id

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

    elif data == "brew_create":
        # Відображення клавіатури з інгредієнтами
        ingredients = get_alcohol_ingredients()
        buttons = [[InlineKeyboardButton(text=ing, callback_data=f"brew_ing|{ing}")] for ing in ingredients]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        buttons = [
            [InlineKeyboardButton(text=ing, callback_data=f"brew_ing|{ing}")]
            for ing in ingredients
        ]
        keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
        await callback_query.message.edit_text("Вибери перший інгредієнт", reply_markup=keyboard)
        await callback_query.answer()

    elif data.startswith("brew_ing|"):
        # 1) Дістаємо назву і додаємо в сесію
        ing = data.split("|", 1)[1]
        if len(session["ingredients"]) < 4:
            session["ingredients"].append(ing)
        else:
            await callback_query.answer("Ви вже вибрали 4 інгредієнти", show_alert=True)
            return

        # 2) Якщо ще менше ніж 4 – питаємо наступний інгредієнт
        if len(session["ingredients"]) < 4:
            ingredients = get_alcohol_ingredients()
            buttons = [
                [InlineKeyboardButton(text=ingr, callback_data=f"brew_ing|{ingr}")]
                for ingr in ingredients
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback_query.message.edit_text(
                f"Вибери інгредієнт {len(session['ingredients']) + 1}/4",
                reply_markup=keyboard
            )
        # 3) Якщо рівно 4 – переходимо до вибору процесу
        else:
            processes = get_alcohol_processes()
            buttons = [
                [InlineKeyboardButton(text=f"{proc} (-{cost})", callback_data=f"brew_proc|{proc}|{cost}")]
                for proc, cost in processes
            ]
            keyboard = InlineKeyboardMarkup(inline_keyboard=buttons)
            await callback_query.message.edit_text(
                "Усі інгредієнти вибрані. Тепер оберіть процес приготування:",
                reply_markup=keyboard
            )

        await callback_query.answer()


    elif data.startswith("brew_proc|"):
        # Обробка вибору процесу
        parts = data.split("|")
        if len(parts) < 3:
            await callback_query.answer("Некоректні дані процесу", show_alert=True)
            return
        proc = parts[1]
        try:
            cost = float(parts[2])
        except ValueError:
            await callback_query.answer("Некоректна вартість процесу", show_alert=True)
            return
        session["processes"].append({"process": proc, "cost": cost})
        # Якщо вибрано менше 4 інгредієнтів – показуємо клавіатуру для вибору наступного інгредієнту без кнопки завершення
        if len(session["ingredients"]) < 4:
            ingredients = get_alcohol_ingredients()
            keyboard = InlineKeyboardMarkup(
                inline_keyboard = [
                    [
                        InlineKeyboardButton(text="Створити",
                        callback_data="brew_create"),
                        InlineKeyboardButton(text="Закрити",
                        callback_data="brew_close")
                    ]
                ]
            )
            await callback_query.message.edit_text("Вибери наступний інгредієнт", reply_markup=keyboard)
        else:
            # Якщо вже вибрано 4 інгредієнти – показуємо клавіатуру з кнопкою завершення
            keyboard = InlineKeyboardMarkup(
                inline_keyboard = [
                     [InlineKeyboardButton(text="Завершити приготування",
                      callback_data="brew_finish")]
                ]
            )
            await callback_query.message.edit_text("Ви вибрали 4 інгредієнти. Завершіть приготування.", reply_markup=keyboard)
        await callback_query.answer()

    elif data == "brew_finish":
        # Фінальний крок – завершення процесу
        total_cost = sum(item["cost"] for item in session["processes"])

        # Перевіряємо, чи існує користувач у таблиці users; якщо ні — додаємо його з початковим рахунком (наприклад, 1000)
        user_id_str = str(user_id)
        con = sqlite3.connect("main.db")
        cur = con.cursor()
        cur.execute("SELECT account FROM users WHERE id = ?", (user_id_str,))
        row = cur.fetchone()
        if not row:
            cur.execute("INSERT INTO users (id, username, account) VALUES (?, ?, ?)",
                        (user_id_str, callback_query.from_user.full_name, 1000))
            current_account = 1000
        else:
            current_account = row[0]

        n = current_account - total_cost
        if n < 0:
            await callback_query.message.edit_text("Недостатньо шекелів. Продукт не було виготовлено")
            return
        else:
            new_account = current_account - total_cost
        cur.execute("UPDATE users SET account = ? WHERE id = ?", (new_account, user_id_str))
        con.commit()
        con.close()

        # Формуємо дані продукту для порівняння з таблицею alcohol_base
        ings = session["ingredients"]
        ings += [""] * (4 - len(ings))  # Заповнюємо, якщо вибрано менше 4 інгредієнтів
        processes_str = ", ".join([p["process"] for p in session["processes"]])
        alcohol_title = session["alcohol_name"]

        # Порівнюємо з таблицею alcohol_base (за назвою, інгредієнтами та процесом)
        con = sqlite3.connect("main.db")
        cur = con.cursor()
        cur.execute("""SELECT * FROM alcohol_base 
                       WHERE title = ? 
                         AND ing1 = ? 
                         AND ing2 = ? 
                         AND ing3 = ? 
                         AND ing4 = ? 
                         AND process = ?""",
                    (alcohol_title, ings[0], ings[1], ings[2], ings[3], processes_str))
        base_match = cur.fetchone()
        if base_match:
            # Якщо продукт знайдено в базі, обчислюємо його витримку.
            # Припустимо, що момент приготування — сьогодні, тому різниця в днях буде 0.
            production_date = datetime.date.today()
            exposure = 0  # на момент створення
            value = exposure * 10  # коефіцієнт
            cur.execute(
                "INSERT INTO alcohol_inventory (id, title, exposure, value, production_date) VALUES (?, ?, ?, ?, ?)",
                (user_id, alcohol_title, exposure, value, production_date.isoformat()))
            inventory_message = "Продукт приготовано згідно рецепту, запис додано до інвентарю."
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

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())
