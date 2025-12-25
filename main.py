import asyncio
import random
from decouple import config

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from db import (get_user, save_user,get_participant_by_name,get_all_participant_ids,
                save_assignments,get_assignment,create_tables,
                add_participant_db,remove_participant_db)


# ================= CONFIG =================

BOT_TOKEN = config("BOT_TOKEN")
ADMIN_ID = config("ADMIN_ID")         # admin telegram ID
GROUP_ID = config("GROUP_ID")        # group ID


# ================= SECRET SANTA ===========
def generate_pairs(ids):
    while True:
        shuffled = ids[:]
        random.shuffle(shuffled)
        if all(a != b for a, b in zip(ids, shuffled)):
            return list(zip(ids, shuffled))
# =========================================


# ================= FSM ====================
class Form(StatesGroup):
    name = State()
# =========================================


dp = Dispatcher()

def is_admin(user_id):
    return user_id == int(ADMIN_ID)


# ================= HANDLERS ===============

@dp.message(commands=["start"])
async def start(message: Message, state: FSMContext):
    await message.answer("Ismingizni kiriting:")
    await state.set_state(Form.name)


@dp.message(Form.name)
async def check_name(message: Message, state: FSMContext):
    name = message.text.strip().lower()

    participant = get_participant_by_name(name)
    if not participant:
        await message.answer("❌ Siz ro‘yxatda yo‘qsiz")
        return

    save_user(message.from_user.id, participant[0])

    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎁 Boshlash")]],
        resize_keyboard=True
    )

    await message.answer("🎄 Boshlash tugmasini bosing", reply_markup=kb)
    await state.clear()


@dp.message(F.text == "🎁 Boshlash")
async def start_santa(message: Message):
    bot = dp["bot"]

    user = get_user(message.from_user.id)
    old = get_assignment(user[0])

    if old:
        await message.answer(
            f"🎁 Siz sovg‘ani **{old[0].title()}** ga berasiz"
        )
        return

    ids = get_all_participant_ids()
    pairs = generate_pairs(ids)
    save_assignments(pairs)

    receiver = get_assignment(user[0])

    await message.answer(
        f"🎉 Siz sovg‘ani **{receiver[0].title()}** ga berasiz!"
    )

    await bot.send_message(
        GROUP_ID,
        f"🎄 Secret Santa!\n"
        f"🎁 {user[1].title()} → {receiver[0].title()}\n"
        f"👏 Tabriklaymiz!"
    )


# ================= ADMIN ==================

@dp.message(commands=["add"])
async def admin_add(message: Message):
    if not is_admin(message.from_user.id):
        return

    name = message.get_args().strip().lower()
    if not name:
        await message.answer("❗ /add ism")
        return

    try:
        add_participant_db(name)
        await message.answer(f"✅ {name.title()} qo‘shildi")
    except:
        await message.answer("⚠️ Bu ism allaqachon mavjud")


@dp.message(commands=["remove"])
async def admin_remove(message: Message):
    if not is_admin(message.from_user.id):
        return

    name = message.get_args().strip().lower()
    if not name:
        await message.answer("❗ /remove ism")
        return

    deleted = remove_participant_db(name)
    if deleted == 0:
        await message.answer("❌ Topilmadi")
    else:
        await message.answer(f"🗑 {name.title()} o‘chirildi")


# ================= RUN ====================

async def main():
    create_tables()  # DB avtomatik yaratiladi
    bot = Bot(BOT_TOKEN, parse_mode="HTML")
    dp["bot"] = bot
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
