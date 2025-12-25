import asyncio
import random
import signal
from decouple import config
import asyncpg

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.filters import Command
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from db import (
    get_all_participant_ids,get_all_assignments_for_users,get_all_participants,get_assignment,
    get_participant_by_name,get_user,save_assignments,save_user,clear_database,create_tables,add_participant_db,
    remove_participant_db,DB_CONFIG
)

# ================= CONFIG =================
BOT_TOKEN = config("BOT_TOKEN")
ADMIN_IDS = [int(x) for x in config("ADMIN_IDS").split(",")]

# ================= SECRET SANTA =================

def generate_pairs(ids, max_attempts=1000):
    if len(ids) < 2:
        raise ValueError("Kamida 2 ishtirokchi bo‘lishi kerak")
    for _ in range(max_attempts):
        shuffled = ids[:]
        random.shuffle(shuffled)
        if all(a != b for a, b in zip(ids, shuffled)):
            return list(zip(ids, shuffled))
    raise ValueError("Valid pairlarni yaratib bo‘lmadi")

# ================= FSM ====================

class Form(StatesGroup):
    name = State()

# ================= BOT ====================

dp = Dispatcher()
pool: asyncpg.pool.Pool = None

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

# ================= HANDLERS =================

@dp.message(Command(commands=["start"]))
async def start(message: Message, state: FSMContext):
    await message.answer("<b>🎄 Secret Santa botiga xush kelibsiz!\n\nIsmingizni kiriting:</b>",parse_mode="HTML")
    await state.set_state(Form.name)

@dp.message(Form.name)
async def check_name(message: Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎁 Boshlash")]],
        resize_keyboard=True
    )
    name = message.text.strip().lower()
    participant = await get_participant_by_name(pool, name)
    if not participant:
        await message.answer("<b>❌ Siz ro‘yxatda yo‘qsiz.\n\n Adminga yozib qayta /start bosing.</b>",parse_mode='HTML')
        await state.clear()

    await save_user(pool, message.from_user.id, participant["id"])
    await state.clear()
    await message.answer(f"✅ {name.title()} saqlandi,\n\n🎁 Boshlash tugmasini bosing",reply_markup=kb,)

@dp.message(F.text == "🎁 Boshlash")
async def start_santa(message: Message):
    user = await get_user(pool, message.from_user.id)
    if not user:
        await message.answer("<b>❌ Avval ismingizni kiritishingiz kerak. \n\n/start bosing ismingizni kiriting: </b>",parse_mode='HTML')
        return

    old = await get_assignment(pool, user["id"])
    if old:
        await message.answer(f"🎁 Siz sovg‘ani <b>{old['receiver_name'].title()}</b> ga berasiz",parse_mode='HTML')
        return

    ids = await get_all_participant_ids(pool)
    try:
        pairs = generate_pairs(ids)
    except ValueError:
        await message.answer("⚠️ Taqsimotni yaratib bo‘lmadi, keyinroq urinib ko‘ring ishtirokchi kam.")
        return

    await save_assignments(pool, pairs)
    receiver = await get_assignment(pool, user["id"])
    await message.answer(f"🎉 Siz sovg‘ani <b>{receiver['receiver_name'].title()}</b> ga berasiz!",parse_mode='HTML')

# ================= ADMIN COMMANDS ==================

@dp.message(Command(commands=["participants"]))
async def cmd_participants(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Faqat admin ishlata oladi")
        return
    participants = await get_all_participants(pool)
    if not participants:
        await message.answer("❌ Hozircha ishtirokchi yo‘q")
        return
    text = "🎄 Ishtirokchilar ro‘yxati:\n" + "\n".join(f"• {n.title()}" for n in participants)
    await message.answer(text)

@dp.message(Command(commands=["assignments"]))
async def cmd_assignments(message: Message):
    if not is_admin(message.from_user.id):
        await message.answer("❌ Faqat admin ishlata oladi")
        return
    assignments = await get_all_assignments_for_users(pool)
    if not assignments:
        await message.answer("❌ Hozircha sovg‘a taqsimoti yo‘q")
        return
    text = "🎁 Secret Santa taqsimoti:\n" + "\n".join(f"• {g.title()} → {r.title()}" for g,r in assignments)
    await message.answer(text)

@dp.message(Command(commands=["add"]))
async def admin_add(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❗ /add ism")
        return
    name = parts[1].strip().lower()
    success = await add_participant_db(pool, name)
    await message.answer(f"✅ {name.title()} qo‘shildi" if success else "⚠️ Bu ism allaqachon mavjud")

@dp.message(Command(commands=["remove"]))
async def admin_remove(message: Message):
    if not is_admin(message.from_user.id):
        return
    parts = message.text.split(maxsplit=1)
    if len(parts) < 2:
        await message.answer("❗ /remove ism")
        return
    name = parts[1].strip().lower()
    deleted = await remove_participant_db(pool, name)
    await message.answer("🗑 O‘chirildi" if deleted else "❌ Topilmadi")

@dp.message(Command(commands=["clear"]))
async def admin_clear(message: Message):
    if not is_admin(message.from_user.id):
        return
    await clear_database(pool)
    await message.answer("🗑 Barcha ma'lumotlar tozalandi!")

# ================= RUN ====================

async def main():
    global pool
    pool = await asyncpg.create_pool(**DB_CONFIG)
    await create_tables(pool)

    bot = Bot(BOT_TOKEN)
    dp["bot"] = bot

    polling_task = asyncio.create_task(dp.start_polling(bot))

    stop_event = asyncio.Event()

    def stop_signal(*args):
        stop_event.set()

    loop = asyncio.get_running_loop()
    loop.add_signal_handler(signal.SIGTERM, stop_signal)
    loop.add_signal_handler(signal.SIGINT, stop_signal)

    await stop_event.wait()
    polling_task.cancel()
    await bot.session.close()
    await pool.close()

if __name__ == "__main__":
    asyncio.run(main())
