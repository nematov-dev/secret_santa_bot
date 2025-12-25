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

# ================= CONFIG =================
BOT_TOKEN = config("BOT_TOKEN")
ADMIN_ID = int(config("ADMIN_ID"))
GROUP_IDS = [int(gid) for gid in config("GROUP_IDS").split(",")]

DB_CONFIG = {
    "user": config("DB_USER"),
    "password": config("DB_PASSWORD"),
    "database": config("DB_NAME"),
    "host": "localhost",
    "port": 5432
}

# ================= DATABASE =================

async def create_tables(pool):
    async with pool.acquire() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS participants (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) UNIQUE NOT NULL
            );
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                tg_id BIGINT UNIQUE NOT NULL,
                participant_id INTEGER REFERENCES participants(id)
            );
            CREATE TABLE IF NOT EXISTS assignments (
                giver_id INTEGER UNIQUE REFERENCES participants(id),
                receiver_id INTEGER REFERENCES participants(id)
            );
        """)

async def add_participant_db(pool, name):
    async with pool.acquire() as conn:
        try:
            await conn.execute("INSERT INTO participants (name) VALUES ($1)", name)
            return True
        except:
            return False

async def remove_participant_db(pool, name):
    async with pool.acquire() as conn:
        result = await conn.execute("DELETE FROM participants WHERE name=$1", name)
        return int(result.split()[-1])

async def clear_database(pool):
    async with pool.acquire() as conn:
        await conn.execute("TRUNCATE TABLE assignments, users, participants RESTART IDENTITY CASCADE")

async def get_participant_by_name(pool, name):
    async with pool.acquire() as conn:
        return await conn.fetchrow("SELECT id FROM participants WHERE name=$1", name)

async def save_user(pool, tg_id, participant_id):
    async with pool.acquire() as conn:
        await conn.execute("""
            INSERT INTO users (tg_id, participant_id)
            VALUES ($1, $2)
            ON CONFLICT (tg_id) DO NOTHING
        """, tg_id, participant_id)

async def get_user(pool, tg_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT p.id, p.name FROM users u
            JOIN participants p ON p.id=u.participant_id
            WHERE u.tg_id=$1
        """, tg_id)

async def get_assignment(pool, giver_id):
    async with pool.acquire() as conn:
        return await conn.fetchrow("""
            SELECT p.name AS receiver_name
            FROM assignments a
            JOIN participants p ON p.id=a.receiver_id
            WHERE a.giver_id=$1
        """, giver_id)

async def get_all_participant_ids(pool):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT id FROM participants")
        return [r["id"] for r in rows]

async def save_assignments(pool, pairs):
    async with pool.acquire() as conn:
        for giver, receiver in pairs:
            await conn.execute("""
                INSERT INTO assignments (giver_id, receiver_id)
                VALUES ($1, $2)
                ON CONFLICT DO NOTHING
            """, giver, receiver)

async def get_all_participants(pool):
    async with pool.acquire() as conn:
        rows = await conn.fetch("SELECT name FROM participants ORDER BY id")
        return [r["name"] for r in rows]

async def get_all_assignments_for_users(pool):
    async with pool.acquire() as conn:
        rows = await conn.fetch("""
            SELECT p1.name AS giver_name, p2.name AS receiver_name
            FROM assignments a
            JOIN participants p1 ON p1.id = a.giver_id
            JOIN participants p2 ON p2.id = a.receiver_id
            ORDER BY p1.name
        """)
        return [(r["giver_name"], r["receiver_name"]) for r in rows]

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
    return user_id == ADMIN_ID

# ================= HANDLERS =================

@dp.message(Command(commands=["start"]))
async def start(message: Message, state: FSMContext):
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🎁 Boshlash")]],
        resize_keyboard=True
    )
    await message.answer("🎄 Secret Santa botiga xush kelibsiz!\nIsmingizni kiriting:", reply_markup=kb)
    await state.set_state(Form.name)

@dp.message(Form.name)
async def check_name(message: Message, state: FSMContext):
    name = message.text.strip().lower()
    participant = await get_participant_by_name(pool, name)
    if not participant:
        await message.answer("❌ Siz ro‘yxatda yo‘qsiz")
        await state.clear()

    await save_user(pool, message.from_user.id, participant["id"])
    await state.clear()
    await message.answer(f"✅ {name.title()} saqlandi, endi 🎁 Boshlash tugmasini bosing")

@dp.message(F.text == "🎁 Boshlash")
async def start_santa(message: Message):
    user = await get_user(pool, message.from_user.id)
    if not user:
        await message.answer("❌ Avval ismingizni kiritishingiz kerak")
        return

    old = await get_assignment(pool, user["id"])
    if old:
        await message.answer(f"🎁 Siz sovg‘ani <b>{old['receiver_name'].title()}</b> ga berasiz")
        return

    ids = await get_all_participant_ids(pool)
    try:
        pairs = generate_pairs(ids)
    except ValueError:
        await message.answer("⚠️ Taqsimotni yaratib bo‘lmadi, keyinroq urinib ko‘ring")
        return

    await save_assignments(pool, pairs)
    receiver = await get_assignment(pool, user["id"])
    await message.answer(f"🎉 Siz sovg‘ani <b>{receiver['receiver_name'].title()}</b> ga berasiz!")

    bot: Bot = dp["bot"]
    for group_id in GROUP_IDS:
        await bot.send_message(
            group_id,
            f"🎄 Secret Santa!\n🎁 {user['name'].title()} → {receiver['receiver_name'].title()} ga sovg'a beradi!\n👏 Tabriklaymiz!"
        )

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
