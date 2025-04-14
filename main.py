import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.filters import CommandStart, Command, CommandObject
from aiogram.types import Message, BotCommand
from handlers import *

# Bot token can be obtained via https://t.me/BotFather
TOKEN = "7713421550:AAG99SbCQsH4q9ke6eeEdiQGDWWGBMyDbj4"

# All handlers should be attached to the Router (or Dispatcher)

dp = Dispatcher()

bot = 0

async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Запустити бота"),
        BotCommand(command="/help", description="Отримати допомогу"),
        BotCommand(command="/addt", description="Додати суму до рахунку"),
        BotCommand(command="/delt", description="Відняти суму від рахунку"),
        BotCommand(command="/topt", description="Топ рахунків"),
        BotCommand(command="/bal", description="Показати баланс"),
    ]
    await bot.set_my_commands(commands)

async def main() -> None:
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    global bot
    bot = Bot(token=TOKEN)

    await set_commands(bot)
    await database.db_start()

    # And the run events dispatching
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
async def add_admin(message: Message) -> None:
    await database.db_add_user(message)

@dp.message(Command("addt"))
async def addt(message : Message, command : object) -> None:
    await database.addt(message, command)

@dp.message(Command("delt"))
async def addt(message : Message, command : object) -> None:
    await database.delt(message, command)

@dp.message(Command("bal"))
async def addt(message : Message) -> None:
    await database.bal(message)

@dp.message(Command("topt"))
async def addt(message : Message, command : object) -> None:
    await database.topt(message, command)









if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    asyncio.run(main())