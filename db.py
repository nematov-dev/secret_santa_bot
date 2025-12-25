import psycopg2
from decouple import config

# ================= DB CONNECTION =================

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
