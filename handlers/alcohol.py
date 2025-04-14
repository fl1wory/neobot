import sqlite3
from aiogram.types import Message
from aiogram.filters import CommandObject

async def db_add_alcohol_ingredients(message: Message, command: object):
    try:
        ing_name = str(command.args)
    except (TypeError, ValueError):
        return

