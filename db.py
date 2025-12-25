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

def get_connection():
    return psycopg2.connect(**DB_CONFIG)


# ================= DB FUNCTIONS =================
def create_tables():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("""
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

    conn.commit()
    cur.close()
    conn.close()



def add_participant_db(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO participants (name) VALUES (%s)",
        (name,)
    )
    conn.commit()
    cur.close()
    conn.close()


def remove_participant_db(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "DELETE FROM participants WHERE name=%s",
        (name,)
    )
    deleted = cur.rowcount
    conn.commit()
    cur.close()
    conn.close()
    return deleted


def get_participant_by_name(name):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute(
        "SELECT id FROM participants WHERE name=%s",
        (name,)
    )
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def save_user(tg_id, participant_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO users (tg_id, participant_id)
        VALUES (%s, %s)
        ON CONFLICT (tg_id) DO NOTHING
    """, (tg_id, participant_id))
    conn.commit()
    cur.close()
    conn.close()


def get_user(tg_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.id, p.name FROM users u
        JOIN participants p ON p.id=u.participant_id
        WHERE u.tg_id=%s
    """, (tg_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_assignment(giver_id):
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT p.name FROM assignments a
        JOIN participants p ON p.id=a.receiver_id
        WHERE a.giver_id=%s
    """, (giver_id,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return row


def get_all_participant_ids():
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("SELECT id FROM participants")
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return [r[0] for r in rows]


def save_assignments(pairs):
    conn = get_connection()
    cur = conn.cursor()
    for giver, receiver in pairs:
        cur.execute("""
            INSERT INTO assignments (giver_id, receiver_id)
            VALUES (%s, %s)
            ON CONFLICT DO NOTHING
        """, (giver, receiver))
    conn.commit()
    cur.close()
    conn.close()
