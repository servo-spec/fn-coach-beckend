import os
import threading
from flask import Flask, request, jsonify
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import database as db
import random

# ============ НАСТРОЙКА ============
TOKEN = os.environ.get("TELEGRAM_TOKEN", "ВАШ_ТОКЕН")

# ============ FLASK (для Render) ============
app = Flask(__name__)

@app.route('/')
@app.route('/health')
def health():
    return "Bot is running", 200

# ============ API ДЛЯ MINI APP ============
# Простая проверка: берём user_id из заголовка, который шлёт фронт
def get_user_id():
    # В идеале тут надо проверять подпись initData, но для старта сойдёт
    return request.headers.get("X-Telegram-Init-Data", "anonymous")

TRAININGS = {
    "aim": {"name": "🎯 Аим и стрельба", "steps": [
        {"text": "Разминка: Creative 1v1 / Aim Lab", "time": "10 мин"},
        {"text": "Тренировка спрея", "time": "15 мин"},
        {"text": "Zone Wars / Box Fights", "time": "15 мин"},
        {"text": "Разбор реплея", "time": "10 мин"},
    ], "total": 50},
    "build": {"name": "🏗️ Билдинг", "steps": [
        {"text": "90s, рампы, базовые комбо", "time": "10 мин"},
        {"text": "Редактирование + перестройка", "time": "15 мин"},
        {"text": "BHE / Free Build", "time": "15 мин"},
        {"text": "Разбор клипа", "time": "10 мин"},
    ], "total": 50},
    "game_sense": {"name": "🧠 Игровое мышление", "steps": [
        {"text": "Матч про-игрока с разбором", "time": "20 мин"},
        {"text": "Разбор своих смертей", "time": "15 мин"},
        {"text": "План на 3 ранкед-матча", "time": "10 мин"},
    ], "total": 45},
    "ranked": {"name": "🏆 Ранкед-сессия", "steps": [
        {"text": "Разминка перед ранкедом", "time": "15 мин"},
        {"text": "Ранкед: фокус на 1 ошибке", "time": "60 мин"},
        {"text": "Перерыв", "time": "15 мин"},
        {"text": "Разбор", "time": "10 мин"},
    ], "total": 100},
}

RANKED_ADVICE = [
    "Не играй на усталости — 3 поражения подряд = стоп на 30 мин.",
    "Перед ранкедом выбери ОДНУ ошибку и следи только за ней.",
    "Лучший ранг берётся за 2-3 короткие сессии, а не за 8 часов подряд.",
    "Если тильтуешь — закрой игру, разбери 1 смерть в реплее.",
    "Не меняй точку высадки каждый матч — стабильность даёт понимание таймингов.",
]

@app.route('/api/training/today')
def training_today():
    import datetime
    keys = ["aim","build","game_sense","ranked","aim","build","rest"]
    k = keys[datetime.date.today().weekday()]
    if k == "rest":
        return jsonify({"type": "rest", "name": "😴 Отдых", "steps": [
            {"text": "Разбор реплеев", "time": "20 мин"},
            {"text": "Отдых от игры", "time": "весь день"},
        ], "total": 20})
    t = TRAININGS[k].copy()
    t["type"] = k
    return jsonify(t)

@app.route('/api/training/week')
def training_week():
    days = ["Пн","Вт","Ср","Чт","Пт","Сб","Вс"]
    keys = ["aim","build","game_sense","ranked","aim","build","rest"]
    result = []
    for d, k in zip(days, keys):
        name = "😴 отдых / разбор реплеев" if k == "rest" else TRAININGS[k]["name"]
        result.append({"day": d, "name": name})
    return jsonify(result)

@app.route('/api/mistakes', methods=['GET'])
def get_mistakes():
    rows = db.get_mistakes()
    return jsonify([{"id": r[0], "text": r[1]} for r in rows])

@app.route('/api/mistakes', methods=['POST'])
def add_mistake():
    data = request.get_json()
    db.add_mistake(data.get("text", ""))
    return jsonify({"ok": True})

@app.route('/api/mistakes/<int:mid>/fix', methods=['PATCH'])
def fix_mistake(mid):
    db.fix_mistake(mid)
    return jsonify({"ok": True})

@app.route('/api/sessions', methods=['POST'])
def add_session():
    data = request.get_json()
    db.add_session(data.get("type", "other"), data.get("duration", 0), "done")
    return jsonify({"ok": True})

@app.route('/api/ranked/advice')
def ranked_advice():
    return jsonify({"advice": random.choice(RANKED_ADVICE)})

@app.route('/api/stats/week')
def stats_week():
    rows = db.week_stats()
    items = [{"type": t, "minutes": m} for t, m in rows]
    total = sum(m for _, m in rows)
    return jsonify({"items": items, "total": total})

# ============ БОТ ============
async def start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я твой тренер по Fortnite 🎮\n"
        "Открой Mini App через кнопку меню.",
        reply_markup=None
    )

def run_bot():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.run_polling()

# ============ ЗАПУСК ============
if __name__ == "__main__":
    db.init()
    # Бот в отдельном потоке, чтобы Flask мог слушать порт
    threading.Thread(target=run_bot, daemon=True).start()
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port)