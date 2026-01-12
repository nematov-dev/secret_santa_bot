# 🎄 Secret Santa Telegram Bot

## 📌 Project Overview

This repository contains a **Telegram bot** for organizing a Secret Santa gift exchange.  
Users can register, start the Secret Santa draw, and receive information about whom they should give a gift to.  
Admins can manage participants, view assignments, and clear or update the database.  

The bot is built with **Python, Aiogram, and async PostgreSQL (`asyncpg`)** and uses **FSM (Finite State Machine)** for user interaction.

---

## 🏢 Features

### User Features
* Start the bot and enter their name
* Receive a notification of the assigned recipient
* View their Secret Santa assignment after it has been created

### Admin Features
* Add new participants: `/add <name>`
* Remove participants: `/remove <name>`
* List all participants: `/participants`
* View all Secret Santa assignments: `/assignments`
* Clear all database records: `/clear`

### Assignment Logic
* Participants are paired randomly
* No participant can be assigned to themselves
* Multiple attempts are made to ensure a valid pairing

---

## 📁 Repository Structure

```
├── bot.py                # Main bot script
├── db.py                 # Database helper functions and asyncpg pool config
├── requirements.txt      # Python dependencies
└── README.md             # This file
```

---

## ⚙️ Technologies & Tools

* Python 3.11+
* [Aiogram](https://docs.aiogram.dev/) – Telegram bot framework
* [asyncpg](https://magicstack.github.io/asyncpg/) – Async PostgreSQL driver
* [python-decouple](https://github.com/henriquebastos/python-decouple) – Manage environment variables
* PostgreSQL – Database for participants and assignments

---

## 🛠 Installation & Setup

1. **Clone the repository:**

```bash
git clone <repository-url>
cd secret-santa-bot
```

2. **Create a virtual environment (optional but recommended):**

```bash
python -m venv .venv
source .venv/bin/activate  # Linux / macOS
.venv\Scripts\activate     # Windows
```

3. **Install dependencies:**

```bash
pip install -r requirements.txt
```

4. **Configure environment variables** (create a `.env` file in the project root):

```
BOT_TOKEN=<your_telegram_bot_token>
ADMIN_IDS=<comma_separated_admin_user_ids>
DB_HOST=localhost
DB_PORT=5432
DB_NAME=secret_santa
DB_USER=<your_db_user>
DB_PASSWORD=<your_db_password>
```

5. **Run the bot:**

```bash
python bot.py
```

> The bot will connect to the database, create tables if needed, and start polling Telegram for messages.

---

## 📝 Usage

### For Users:
1. Start the bot with `/start`
2. Enter your name exactly as registered by the admin
3. Press the “🎁 Start” button to get your Secret Santa assignment

### For Admins:
* Add a participant:

```
/add John
```

* Remove a participant:

```
/remove John
```

* List participants:

```
/participants
```

* View assignments:

```
/assignments
```

* Clear all database records:

```
/clear
```

> Only Telegram users whose IDs are listed in `ADMIN_IDS` can use admin commands.

---

## 📊 Assignment Algorithm

1. Gather all participant IDs from the database  
2. Shuffle participants randomly  
3. Ensure no one is assigned to themselves  
4. Save the assignments in the database  
5. Each participant can view their assigned recipient only after assignments are created  

---

## 🚀 Future Improvements

* Add scheduled automatic assignment on a specific date  
* Add notification reminders to participants  
* Add web interface to manage participants and view assignments  
* Add support for multiple Secret Santa groups  

---

## 👨‍💻 Developer

**Saidakbar Ne'matov**

---

## 📄 License

This project is intended for **educational and demonstration purposes**.
