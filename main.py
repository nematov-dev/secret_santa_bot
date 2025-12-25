import asyncio
import random
from decouple import config

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from db import (
    get_user,
    save_user,
    get_participant_by_name,
    get_all_participant_ids,
    save_assignments,
    get_assignment,
    create_tables,
    add_participant_db,
    remove_participant_db,
    get_all_assignments_for_users,
    get_all_participants
)

# ================= CONFIG =================
BOT_TOKEN = config("BOT_TOKEN")
ADMIN_ID = int(config("ADMIN_ID"))
GROUP_IDS = [int(gid) for gid in config("GROUP_IDS").split(",")]

# ================= SECRET SANTA ===========

def generate_pairs(ids):
    while True:
        shuffled = ids[:]
        random.shuffle(shuffled)
        if all(a != b for a, b in zip(ids, shuffled)):
            return list(zip(ids, shuffled))

# ================= FSM ====================

class Form(StatesGroup):
    name = State()

# ================= BOT ====================

dp = Dispatcher()

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

# ================= HANDLERS ===============

@dp.message(Command(commands=["start"]))
async def start(message: Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎁 Boshlash")],
            [KeyboardButton(text="📋 Ishtirokchilar"), KeyboardButton(text="🎉 Assignments")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🎄 Secret Santa botiga xush kelibsiz!\nIsmingizni kiriting:", 
        reply_markup=kb
    )
    await state.set_state(Form.name)

@dp.message(Form.name)
async def check_name(message: Message, state: FSMContext):
    name = message.text.strip().lower()
    participant = get_participant_by_name(name)
    if not participant:
        await message.answer("❌ Siz ro‘yxatda yo‘qsiz")
        return
    save_user(message.from_user.id, participant[0])
    await state.clear()
    await message.answer(f"✅ {name.title()} saqlandi, endi 🎁 Boshlash tugmasini bosing")

@dp.message(F.text == "🎁 Boshlash")
async def start_santa(message: Message):
    bot: Bot = dp["bot"]
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Avval ismingizni kiritishingiz kerak")
        return

    old = get_assignment(user[0])
    if old:
        await message.answer(f"🎁 Siz sovg‘ani <b>{old[0].title()}</b> ga berasiz")
        return

    ids = get_all_participant_ids()
    pairs = generate_pairs(ids)
    save_assignments(pairs)
    receiver = get_assignment(user[0])

    await message.answer(f"🎉 Siz sovg‘ani <b>{receiver[0].title()}</b> ga berasiz!")

    for group_id in GROUP_IDS:
        await bot.send_message(
            group_id,
            f"🎄 Secret Santa!\n"
            f"🎁 {user[1].title()} → {receiver[0].title()} ga sovg'a beradi!\n"
            f"👏 Tabriklaymiz!"
        )

# ================= MENU HANDLERS ===============

@dp.message(F.text == "📋 Ishtirokchilar")
async def menu_participants(message: Message):
    participants = get_all_participants()
    if not participants:
        await message.answer("❌ Hozircha ishtirokchi yo‘q")
        return
    text = "🎄 Ishtirokchilar ro‘yxati:\n" + "\n".join(f"• {name.title()}" for name in participants)
    await message.answer(text)

@dp.message(F.text == "🎉 Assignments")
async def menu_assignments(message: Message):
    assignments = get_all_assignments_for_users()
    if not assignments:
        await message.answer("❌ Hozircha sovg‘a taqsimoti yo‘q")
        return
    text = "🎁 Secret Santa taqsimoti:\n"
    for giver, receiver in assignments:
        text += f"• {giver.title()} → {receiver.title()}\n"
    await message.answer(text)

# ================= ADMIN ==================

@dp.message(Command(commands=["add"]))
async def admin_add(message: Message):
    if not is_admin(message.from_user.id):
        return
    
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❗ /add ism")
        return
    
    name = parts[1].strip().lower()
    try:
        add_participant_db(name)
        await message.answer(f"✅ {name.title()} qo‘shildi")
    except:
        await message.answer("⚠️ Bu ism allaqachon mavjud")

@dp.message(Command(commands=["remove"]))
async def admin_remove(message: Message):
    if not is_admin(message.from_user.id):
        return

    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❗ /remove ism")
        return
    
    name = parts[1].strip().lower()
    deleted = remove_participant_db(name)
    if deleted == 0:
        await message.answer("❌ Topilmadi")
    else:
        await message.answer(f"🗑 {name.title()} o‘chirildi")

# ================= RUN ====================

async def main():
    create_tables()
    bot = Bot(BOT_TOKEN)  # aiogram 3.22.0
    dp["bot"] = bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
