import os
import threading
import random
import datetime
import sqlite3
from flask import Flask
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, 
    MessageHandler, filters, ConversationHandler, ContextTypes
)

# ============ НАСТРОЙКА ============
TOKEN = os.environ.get("TELEGRAM_TOKEN", "ВАШ_ТОКЕН")
DB_FILE = "coach_pro.db"

# ============ БАЗА ДАННЫХ ============
def init_db():
    con = sqlite3.connect(DB_FILE)
    cur = con.cursor()
    cur.execute("""CREATE TABLE IF NOT EXISTS mistakes (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, text TEXT, date TEXT)""")
    cur.execute("""CREATE TABLE IF NOT EXISTS logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT, 
        user_id INTEGER, date TEXT, activity TEXT)""")
    con.commit()
    con.close()

def add_mistake(user_id, text):
    con = sqlite3.connect(DB_FILE)
    con.execute("INSERT INTO mistakes (user_id, text, date) VALUES (?, ?, ?)", 
                (user_id, text, datetime.date.today().isoformat()))
    con.commit()
    con.close()

def get_mistakes(user_id):
    con = sqlite3.connect(DB_FILE)
    rows = con.execute("SELECT id, text FROM mistakes WHERE user_id = ?", (user_id,)).fetchall()
    con.close()
    return rows

def add_log(user_id, activity):
    con = sqlite3.connect(DB_FILE)
    con.execute("INSERT INTO logs (user_id, date, activity) VALUES (?, ?, ?)", 
                (user_id, datetime.date.today().isoformat(), activity))
    con.commit()
    con.close()

def get_weekly_logs(user_id):
    week_ago = (datetime.date.today() - datetime.timedelta(days=7)).isoformat()
    con = sqlite3.connect(DB_FILE)
    rows = con.execute("SELECT activity, COUNT(*) FROM logs WHERE user_id = ? AND date >= ? GROUP BY activity", 
                       (user_id, week_ago)).fetchall()
    con.close()
    return rows

# ============ ДАННЫЕ ============
TRAININGS = {
    "aim": {
        "name": "🎯 АИМ И МЕХАНИКА (Обязательно)",
        "steps": [
            "1. Aim Lab / Коваки: 15 мин (фокус на точность, а не скорость)",
            "2. Creative 1v1 с ботом: 10 мин",
            "3. Zone Wars (реалистик): 20 мин (учись играть от укрытий)",
            "4. Разбор: посмотри 1 свой клип со стороны, найди 3 промаха"
        ]
    },
    "build": {
        "name": "🏗️ БИЛДИНГ И РЕДАКТИРОВАНИЕ",
        "steps": [
            "1. Спринт-билдинг (90s, рампы): 10 мин",
            "2. Редактирование стен и конусов: 15 мин (до идеала)",
            "3. BHE (Box Fight): 20 мин",
            "4. Ошибки: где тебя 'зажали'? Запиши в дневник ошибок."
        ]
    },
    "game_sense": {
        "name": "🧠 ИГРОВОЕ МЫШЛЕНИЕ (Анализ)",
        "steps": [
            "1. Посмотри VOD (разбор) про-игрока: 20 мин",
            "2. Разбор своих смертей за неделю: 15 мин (почему умер?)",
            "3. Составь план на 3 следующие игры: 5 мин",
            "4. Отдохни от игры 1 час."
        ]
    },
    "ranked": {
        "name": "🏆 РАНКЕД-СЕССИЯ (Только с фокусом)",
        "steps": [
            "1. Разминка: 15 мин (аим/билд) - БЕЗ РАНКЕДА",
            "2. Выбери ОДНУ ошибку из дневника. Следи только за ней.",
            "3. Играй 3 матча. Не больше.",
            "4. Сделай перерыв 15 мин. Запиши результаты."
        ]
    },
    "rest": {
        "name": "😴 ВОССТАНОВЛЕНИЕ (Это тоже тренировка)",
        "steps": [
            "1. Никакого Fortnite сегодня.",
            "2. Разомни кисти и глаза.",
            "3. Посмотри обучающее видео по игре (теория).",
            "4. Выспись. Мозг запоминает механику во сне."
        ]
    }
}

RANKED_ADVICE = [
    "Unreal требует стабильности. Если проиграл 2 игры подряд — стоп на 30 минут.",
    "Ты не апнешь ранг, если будешь играть на автомате. В каждой игре ставь микро-цель (например, не умирать в первые 5 минут).",
    "Не меняй точку высадки. Стабильность дает понимание таймингов и лута.",
    "Тильт — твой главный враг. Вышел из себя — закрыл игру. Это дисциплина.",
    "Смотри не на свой ранг, а на свой прогресс. Ты стал лучше строиться? Уже победа."
]

# ============ МЕНЮ ============
def main_menu():
    kb = [
        [InlineKeyboardButton("📋 План на сегодня", callback_data="today")],
        [InlineKeyboardButton("📅 Неделя", callback_data="week"), InlineKeyboardButton("📊 Мой прогресс", callback_data="stats")],
        [InlineKeyboardButton("🧠 Дневник ошибок", callback_data="mistakes")],
        [InlineKeyboardButton("🏆 Иду в ранкед", callback_data="ranked_ready")]
    ]
    return InlineKeyboardMarkup(kb)

# ============ ХЕНДЛЕРЫ ============
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = (
        "🔥 *Личный тренер по Fortnite* 🔥\n\n"
        "Твой путь до анрила тренируйся каждый день.\n\n"
        "Вот твой инструментарий:\n"
        "1️⃣ Смотри план на сегодня и выполняй его.\n"
        "2️⃣ Записывай ошибки (через /mistake).\n"
        "3️⃣ Отмечай тренировки (через /log).\n\n"
        "Начнем?"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu())

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data

    if data == "today":
        keys = ["aim", "build", "game_sense", "ranked", "aim", "build", "rest"]
        k = keys[datetime.date.today().weekday()]
        plan = TRAININGS[k]
        
        text = f"*{plan['name']}*\n\n"
        for step in plan["steps"]:
            text += f"{step}\n"
        
        text += "\n_После выполнения напиши /log, чтобы отметить прогресс._"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

    elif data == "week":
        days = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
        keys = ["aim", "build", "game_sense", "ranked", "aim", "build", "rest"]
        text = "📅 *Твой план на неделю*\n\n"
        for d, k in zip(days, keys):
            text += f"*{d}*: {TRAININGS[k]['name']}\n"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

    elif data == "ranked_ready":
        advice = random.choice(RANKED_ADVICE)
        text = (
            "🏆 *Чек-лист перед ранкедом*\n\n"
            "Проверь себя:\n"
            "✅ Я сделал разминку (аим/билд)?\n"
            "✅ Я выспался и не устал?\n"
            "✅ Я выбрал ОДНУ ошибку для фокуса?\n"
            "✅ У меня есть план на 3 игры?\n\n"
            f"💡 *Совет тренера:*\n_{advice}_"
        )
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

    elif data == "stats":
        logs = get_weekly_logs(user_id)
        if not logs:
            text = "📊 *Прогресс*\n\nПока нет записей. Используй /log после каждой тренировки, чтобы я видел твой прогресс."
        else:
            text = "📊 *Твой прогресс за неделю:*\n\n"
            for act, count in logs:
                text += f"• {act}: {count} раз(а)\n"
            text += "\n_Продолжай в том же духе. Без регулярности Unreal не берется._"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

    elif data == "mistakes":
        mistakes = get_mistakes(user_id)
        if not mistakes:
            text = "🧠 *Дневник ошибок*\n\nТвой дневник пуст. Чтобы стать лучше, ты должен знать свои слабые места. Напиши /mistake, чтобы добавить ошибку."
        else:
            text = "🧠 *Твои ошибки (работай над ними):*\n\n"
            for m_id, m_text in mistakes:
                text += f"❌ {m_text}\n"
            text += "\n_Добавить новую ошибку: /mistake_"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

# ============ КОМАНДЫ ============
# Добавление ошибки (Диалог)
async def add_mistake_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Напиши, какую ошибку ты понял (например: 'умираю от снайперов в открытом поле'):")
    return 1

async def save_mistake(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    add_mistake(update.message.from_user.id, text)
    await update.message.reply_text(f"✅ Ошибка записана:\n_{text}_\n\nТеперь работай над ней в ранкеде.", parse_mode="Markdown")
    return ConversationHandler.END

# Лог тренировки (Диалог)
async def log_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🎯 Аим", callback_data="log_aim"), InlineKeyboardButton("🏗️ Билд", callback_data="log_build")],
        [InlineKeyboardButton("🧠 Теория", callback_data="log_theory"), InlineKeyboardButton("🏆 Ранкед", callback_data="log_ranked")]
    ]
    await update.message.reply_text("Что ты сегодня отработал?", reply_markup=InlineKeyboardMarkup(kb))
    return 1

async def save_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    action = q.data.replace("log_", "")
    add_log(q.from_user.id, action)
    await q.edit_message_text(f"✅ Записал: {action}. Отдыхай, завтра продолжим.")
    return ConversationHandler.END

def run_bot():
    print("=== БОТ ЗАПУСКАЕТСЯ ===", flush=True)
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Обработчик кнопок
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(button_handler))

        # Обработчик ошибок
        conv_mistake = ConversationHandler(
            entry_points=[CommandHandler("mistake", add_mistake_start)],
            states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_mistake)]},
            fallbacks=[]
        )
        application.add_handler(conv_mistake)

        # Обработчик логов
        conv_log = ConversationHandler(
            entry_points=[CommandHandler("log", log_start)],
            states={1: [CallbackQueryHandler(save_log)]},
            fallbacks=[]
        )
        application.add_handler(conv_log)

        print("=== БОТ УСПЕШНО СОЗДАН ===", flush=True)
        application.run_polling()
    except Exception as e:
        print(f"!!! ОШИБКА БОТА: {e} !!!", flush=True)

# ============ ЗАПУСК ============
if __name__ == "__main__":
    print("=== СТАРТ FLASK ===", flush=True)
    init_db()
    
    # Flask в фоне (чтобы Render видел порт)
    app_flask = Flask(__name__)
    @app_flask.route('/')
    def health(): return "Bot is running", 200
    
    port = int(os.environ.get("PORT", 10000))
    flask_thread = threading.Thread(
        target=lambda: app_flask.run(host='0.0.0.0', port=port, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    
    # Бот в главном потоке
    run_bot()
