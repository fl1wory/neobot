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

