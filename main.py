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
            [KeyboardButton("🎁 Boshlash")],
            [KeyboardButton("📋 Ishtirokchilar"), KeyboardButton("🎉 Assignments")]
        ],
        resize_keyboard=True
    )
    await message.answer(
        "🎄 Secret Santa botiga xush kelibsiz!\nIsmingizni kiriting:", 
        reply_markup=kb,
        parse_mode="HTML"
    )
    await state.set_state(Form.name)

@dp.message(Form.name)
async def check_name(message: Message, state: FSMContext):
    name = message.text.strip().lower()
    participant = get_participant_by_name(name)
    if not participant:
        await message.answer("❌ Siz ro‘yxatda yo‘qsiz", parse_mode="HTML")
        return
    save_user(message.from_user.id, participant[0])
    await state.clear()
    await message.answer(f"✅ {name.title()} saqlandi, endi 🎁 Boshlash tugmasini bosing", parse_mode="HTML")

@dp.message(F.text == "🎁 Boshlash")
async def start_santa(message: Message):
    bot: Bot = dp["bot"]
    user = get_user(message.from_user.id)
    if not user:
        await message.answer("❌ Avval ismingizni kiritishingiz kerak", parse_mode="HTML")
        return

    old = get_assignment(user[0])
    if old:
        await message.answer(f"🎁 Siz sovg‘ani <b>{old[0].title()}</b> ga berasiz", parse_mode="HTML")
        return

    ids = get_all_participant_ids()
    pairs = generate_pairs(ids)
    save_assignments(pairs)
    receiver = get_assignment(user[0])

    await message.answer(f"🎉 Siz sovg‘ani <b>{receiver[0].title()}</b> ga berasiz!", parse_mode="HTML")

    for group_id in GROUP_IDS:
        await bot.send_message(
            group_id,
            f"🎄 Secret Santa!\n🎁 {user[1].title()} → {receiver[0].title()} ga sovg'a beradi!\n👏 Tabriklaymiz!",
            parse_mode="HTML"
        )

# ================= MENU HANDLERS ===============

@dp.message(F.text == "📋 Ishtirokchilar")
async def menu_participants(message: Message):
    participants = get_all_participants()
    if not participants:
        await message.answer("❌ Hozircha ishtirokchi yo‘q", parse_mode="HTML")
        return
    text = "🎄 Ishtirokchilar ro‘yxati:\n" + "\n".join(f"• {name.title()}" for name in participants)
    await message.answer(text, parse_mode="HTML")

@dp.message(F.text == "🎉 Assignments")
async def menu_assignments(message: Message):
    assignments = get_all_assignments_for_users()
    if not assignments:
        await message.answer("❌ Hozircha sovg‘a taqsimoti yo‘q", parse_mode="HTML")
        return
    text = "🎁 Secret Santa taqsimoti:\n"
    for giver, receiver in assignments:
        text += f"• {giver.title()} → {receiver.title()}\n"
    await message.answer(text, parse_mode="HTML")

# ================= ADMIN ==================

@dp.message(Command(commands=["add"]))
async def admin_add(message: Message):
    if not is_admin(message.from_user.id):
        return
    name = message.get_args().strip().lower()
    if not name:
        await message.answer("❗ /add ism", parse_mode="HTML")
        return
    try:
        add_participant_db(name)
        await message.answer(f"✅ {name.title()} qo‘shildi", parse_mode="HTML")
    except:
        await message.answer("⚠️ Bu ism allaqachon mavjud", parse_mode="HTML")

@dp.message(Command(commands=["remove"]))
async def admin_remove(message: Message):
    if not is_admin(message.from_user.id):
        return
    name = message.get_args().strip().lower()
    if not name:
        await message.answer("❗ /remove ism", parse_mode="HTML")
        return
    deleted = remove_participant_db(name)
    if deleted == 0:
        await message.answer("❌ Topilmadi", parse_mode="HTML")
    else:
        await message.answer(f"🗑 {name.title()} o‘chirildi", parse_mode="HTML")

# ================= RUN ====================

async def main():
    create_tables()
    bot = Bot(token=BOT_TOKEN)
    dp["bot"] = bot
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
