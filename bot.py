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
    "Ты не апнешь ранг, если будешь играть на автомате. В каждой игре ставь микро-цель.",
    "Не меняй точку высадки. Стабильность дает понимание таймингов и лута.",
    "Тильт — твой главный враг. Вышел из себя — закрыл игру. Это дисциплина.",
    "Смотри не на свой ранг, а на свой прогресс. Ты стал лучше строиться? Уже победа."
]

# ============ БАЗА СОВЕТОВ ПО ОШИБКАМ ============
# Здесь мы ищем ключевые слова в ошибке игрока и даем совет
TIPS_DB = {
    "снайпер": "🎯 Совет: Никогда не стой в открытом поле. Всегда держи в голове укрытие (дерево, камень, холм). Если тебя простреливают — строй стену мгновенно, не жди, пока прилетит вторая пуля.",
    "зажат": "📦 Совет: Если тебя зажали в 1x1 или коробке, не паникуй. Сломай пол и упади вниз, либо делай 'водопад' (waterfall) вниз. Главное — двигайся, а не стой на месте. Научись делать быстрый 90s, чтобы уходить на высоту.",
    "высот": "🏔️ Совет: Высота — это 80% победы в ранкеде. Если ты внизу, а враг сверху — ты в проигрышной позиции. Строй рампы в сторону, уходи из-под обстрела, и пытайся зайти ему в бок.",
    "промах": "🎯 Совет: Промахи — это либо слишком высокая чувствительность (сенса), либо отсутствие разминки. Снизь сенсу на 10%, поиграй в Aim Lab 15 минут перед игрой. И не стреляй на бегу — остановись на долю секунды.",
    "тильт": "🧘 Совет: Тильт убивает ранг. Если чувствуешь злость — закрывай игру. Лучше сделать перерыв 30 минут и выпить воды, чем слить 5 матчей подряд на эмоциях.",
    "ротаци": "🗺️ Совет: Не беги в центр круга. Двигайся по краю, используй естественные укрытия. Всегда оставляй себе путь отхода (стройку).",
    "хп": "🩹 Совет: Не забегай в бой с 50 HP. Всегда долечивайся до 100+ щита перед тем, как стрелять. Если нет щитов — играй пассивно, фарми ресурсы.",
    "дробовик": "🔫 Совет: В ближнем бою (дробовик) главное — не промазать первым выстрелом. Делай флик (резкий разворот) и стреляй в голову. Тренируй это в Creative.",
    "лава": "🌋 Совет: Не прыгай в лаву/воду без необходимости. Это ловушка. Если тебя туда скинули — сразу строй стену под себя, чтобы не утонуть."
}

def get_advice_for_mistake(text):
    text = text.lower()
    for key, advice in TIPS_DB.items():
        if key in text:
            return advice
    return "🤔 Совет: Проанализируй этот момент в реплее. Что ты мог сделать иначе? Запиши решение и применяй в следующем матче."

# ============ МЕНЮ ============
def main_menu():
    kb = [
        [InlineKeyboardButton("📋 План на сегодня", callback_data="today")],
        [InlineKeyboardButton("📅 Неделя", callback_data="week"), InlineKeyboardButton("📊 Мой прогресс", callback_data="stats")],
        [InlineKeyboardButton("🧠 Дневник ошибок", callback_data="mistakes")],
        [InlineKeyboardButton("💡 База знаний", callback_data="knowledge")],
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
        "2️⃣ Записывай ошибки (через /mistake). Я дам совет, как их исправить.\n"
        "3️⃣ Отмечай тренировки (через /log).\n\n"
        "Начнем?"
    )
    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=main_menu())

async def button_handler(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer()
    user_id = q.from_user.id
    data = q.data
    if data.startswith("log_"):
    # Если это кнопка лога, отдаем её функции save_log
    return await save_log(update, ctx)

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
            text = "🧠 *Дневник ошибок*\n\nТвой дневник пуст. Напиши /mistake, чтобы добавить ошибку и получить совет."
        else:
            text = "🧠 *Твои ошибки (и советы):*\n\n"
            for m_id, m_text in mistakes:
                text += f"❌ _{m_text}_\n"
                text += f"{get_advice_for_mistake(m_text)}\n\n"
            text += "Добавить новую: /mistake"
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

    elif data == "knowledge":
        text = (
            "💡 *База знаний тренера*\n\n"
            "Топ-3 правила для аппа ранга:\n\n"
            "1️⃣ *Играй на выживание, а не на киллы.* В ранкеде победа дает больше очков, чем 5 киллов и смерть на 20 месте.\n\n"
            "2️⃣ *Всегда долечивайся.* Здоровье важнее лута. Если у тебя 50 HP — ты не имеешь права идти в бой.\n\n"
            "3️⃣ *Держи высоту.* В Форточке тот, кто сверху — диктует правила игры. Учись делать быстрый 90s.\n\n"
            "_Используй /mistake, чтобы получить совет по конкретной проблеме._"
        )
        await q.edit_message_text(text, parse_mode="Markdown", reply_markup=main_menu())

# ============ КОМАНДЫ ============
async def add_mistake_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Напиши, какую ошибку ты понял (например: 'умираю от снайперов в открытом поле'):")
    return 1

async def save_mistake(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    add_mistake(update.message.from_user.id, text)
    advice = get_advice_for_mistake(text)
    
    await update.message.reply_text(
        f"✅ Ошибка записана:\n_{text}_\n\n{advice}\n\n_Теперь работай над ней в ранкеде._", 
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def log_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    kb = [
        [InlineKeyboardButton("🎯 Аим", callback_data="log_aim"), InlineKeyboardButton("🏗️ Билд", callback_data="log_build")],
        [InlineKeyboardButton("🧠 Теория", callback_data="log_theory"), InlineKeyboardButton("🏆 Ранкед", callback_data="log_ranked")]
    ]
    await update.message.reply_text("Что ты сегодня отработал?", reply_markup=InlineKeyboardMarkup(kb))
    return 1

async def save_log(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    q = update.callback_query
    await q.answer() # Убирает анимацию загрузки на кнопке
    
    try:
        action = q.data.replace("log_", "")
        print(f"ПОЛУЧЕН ЛОГ: {action} от {q.from_user.id}", flush=True)
        
        add_log(q.from_user.id, action)
        
        await q.edit_message_text(f"✅ Записал: {action}. Отдыхай, завтра продолжим.")
    except Exception as e:
        print(f"!!! ОШИБКА В ЛОГАХ: {e} !!!", flush=True)
        # Если что-то пошло не так, бот хотя бы ответит, а не молчит
        await q.edit_message_text(f"⚠️ Ошибка записи: {e}")
# ============ ХЕНДЛЕРЫ ============
async def add_mistake_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("📝 Напиши, какую ошибку ты понял (например: 'умираю от снайперов в открытом поле'):")
    return 1

async def save_mistake(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    add_mistake(update.message.from_user.id, text)
    advice = get_advice_for_mistake(text)
    
    await update.message.reply_text(
        f"✅ Ошибка записана:\n_{text}_\n\n{advice}\n\n_Теперь работай над ней в ранкеде._", 
        parse_mode="Markdown"
    )
    return ConversationHandler.END

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

# --- НОВАЯ ФУНКЦИЯ ОТМЕНЫ ---
async def cancel(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Действие отменено. Возвращайся в меню через /start.")
    return ConversationHandler.END
def run_bot():
    print("=== БОТ ЗАПУСКАЕТСЯ ===", flush=True)
    try:
        application = Application.builder().token(TOKEN).build()
        
        # Главное меню и кнопки
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CallbackQueryHandler(save_log))
        
        # Обработчик для логов (просто ловит кнопки)
        application.add_handler(CommandHandler("log", log_start))
        print("!!! ОБРАБОТЧИКИ ЗАГРУЖЕНЫ !!!", flush=True)
        application.add_handler(CallbackQueryHandler(save_log, pattern="^log_"))

        # Обработчик ошибок (диалог оставляем, он работал)
        conv_mistake = ConversationHandler(
            entry_points=[CommandHandler("mistake", add_mistake_start)],
            states={1: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_mistake)]},
            fallbacks=[CommandHandler("cancel", cancel)],
        )
        application.add_handler(conv_mistake)

        print("=== БОТ УСПЕШНО СОЗДАН ===", flush=True)
        application.run_polling(stop_signals=None)
    except Exception as e:
        print(f"!!! ОШИБКА БОТА: {e} !!!", flush=True)
if __name__ == "__main__":
    print("=== СТАРТ ПРИЛОЖЕНИЯ ===", flush=True)
    init_db()
    
    # 1. Запускаем Flask в ФОНОВОМ потоке (он просто слушает порт)
    from flask import Flask
    app_flask = Flask(__name__)
    
    @app_flask.route('/')
    def health(): 
        return "Bot is running", 200
    
    port = int(os.environ.get("PORT", 10000))
    flask_thread = threading.Thread(
        target=lambda: app_flask.run(host='0.0.0.0', port=port, use_reloader=False), 
        daemon=True
    )
    flask_thread.start()
    print(f">>> FLASK ЗАПУЩЕН НА ПОРТУ {port} В ФОНЕ <<<", flush=True)
    
    # 2. Запускаем БОТА в ГЛАВНОМ потоке
    print(">>> БОТ ЗАПУСКАЕТСЯ В ГЛАВНОМ ПОТОКЕ <<<", flush=True)
    run_bot()
