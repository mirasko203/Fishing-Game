import telebot
from telebot import types
import sqlite3
import random
import time

TOKEN = "8400511241:AAFwWPyBDg8us2oy7CM0miKcP4li0iM2TdU"
bot = telebot.TeleBot(TOKEN)

# ================== БАЗА ДАННЫХ ==================
conn = sqlite3.connect("db.sqlite3", check_same_thread=False)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS users (
    user_id INTEGER PRIMARY KEY,
    money INTEGER,
    level INTEGER,
    rod INTEGER,
    location TEXT,
    last_fish INTEGER,
    bait TEXT,
    bait_bread INTEGER,
    bait_worm INTEGER,
    bait_maggot INTEGER,
    bait_corn INTEGER,
    bait_blood INTEGER,
    quest_fish TEXT,
    quest_need INTEGER,
    quest_done INTEGER
)
""")
conn.commit()

# ================== ДАННЫЕ ==================
RODS = {
    1: {"name": "Старая удочка", "chance": 50, "price": 0},
    2: {"name": "Хорошая удочка", "chance": 70, "price": 200},
    3: {"name": "Профи удочка", "chance": 90, "price": 500},
}

BAITS = {
    "Хлеб": {"bonus": 0, "price": 1},
    "Червь": {"bonus": 10, "price": 3},
    "Опарыш": {"bonus": 15, "price": 5},
    "Кукуруза": {"bonus": 20, "price": 8},
    "Мотыль": {"bonus": 30, "price": 12},
}

BAIT_INDEX = {
    "Хлеб": 7,
    "Червь": 8,
    "Опарыш": 9,
    "Кукуруза": 10,
    "Мотыль": 11,
}

BAIT_COLUMN = {
    "Хлеб": "bait_bread",
    "Червь": "bait_worm",
    "Опарыш": "bait_maggot",
    "Кукуруза": "bait_corn",
    "Мотыль": "bait_blood",
}

FISH = {
    "Река": [("Карась", 10), ("Щука", 40)],
    "Озеро": [("Карась", 10), ("Щука", 40), ("Лосось", 120)],
    "Море": [("Лосось", 120), ("Тунец", 200)],
}

LOCATIONS = {
    "Река": 0,
    "Озеро": 300,
    "Море": 700,
}

QUEST_FISH = ["Карась", "Щука", "Лосось", "Тунец"]

# ================== ФУНКЦИИ ==================
def get_user(uid):
    cursor.execute("SELECT * FROM users WHERE user_id=?", (uid,))
    return cursor.fetchone()

def create_user(uid):
    cursor.execute("""
    INSERT INTO users VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        uid, 100, 1, 1, "Река", 0,
        "Хлеб", 100, 0, 0, 0, 0,
        "", 0, 0
    ))
    conn.commit()
    new_quest(uid)

def update_user(uid, field, value):
    cursor.execute(f"UPDATE users SET {field}=? WHERE user_id=?", (value, uid))
    conn.commit()

def new_quest(uid):
    fish = random.choice(QUEST_FISH)
    need = random.randint(3, 7)
    cursor.execute("""
    UPDATE users SET quest_fish=?, quest_need=?, quest_done=0 WHERE user_id=?
    """, (fish, need, uid))
    conn.commit()

def main_menu():
    kb = types.InlineKeyboardMarkup()
    kb.add(
        types.InlineKeyboardButton("🎣 Ловить", callback_data="fish"),
        types.InlineKeyboardButton("🎯 Наживка", callback_data="select_bait")
    )
    kb.add(
        types.InlineKeyboardButton("📜 Квесты", callback_data="quest"),
        types.InlineKeyboardButton("🛒 Магазин", callback_data="shop")
    )
    kb.add(
        types.InlineKeyboardButton("🗺 Локации", callback_data="locations"),
        types.InlineKeyboardButton("🎒 Профиль", callback_data="profile")
    )
    return kb

# ================== START ==================
@bot.message_handler(commands=["start"])
def start(msg):
    if not get_user(msg.from_user.id):
        create_user(msg.from_user.id)
    bot.send_message(msg.chat.id, "🎣 Добро пожаловать в симулятор рыбалки!", reply_markup=main_menu())

# ================== CALLBACK ==================
@bot.callback_query_handler(func=lambda call: True)
def callback(call):
    uid = call.from_user.id
    user = get_user(uid)

    # -------- ПРОФИЛЬ --------
    if call.data == "profile":
        text = (
            f"🎒 Профиль\n\n"
            f"💰 Деньги: {user[1]}\n"
            f"⭐ Уровень: {user[2]}\n"
            f"🎣 Удочка: {RODS[user[3]]['name']}\n"
            f"🎯 Активная наживка: {user[6]}\n"
            f"🗺 Локация: {user[4]}"
        )
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=main_menu())

    # -------- ВЫБОР НАЖИВКИ --------
    elif call.data == "select_bait":
        kb = types.InlineKeyboardMarkup()
        for bait in BAITS:
            count = user[BAIT_INDEX[bait]]
            kb.add(types.InlineKeyboardButton(f"{bait} ({count})", callback_data=f"usebait_{bait}"))
        kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="back"))
        bot.edit_message_text("🎯 Выберите активную наживку", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data.startswith("usebait_"):
        bait = call.data.split("_")[1]
        update_user(uid, "bait", bait)
        bot.answer_callback_query(call.id, f"🎯 Активная наживка: {bait}")

    # -------- ЛОВЛЯ --------
    elif call.data == "fish":
        now = int(time.time())
        if now - user[5] < 5:
            bot.answer_callback_query(call.id, f"⏳ Подожди {5 - (now - user[5])} сек.")
            return

        bait = user[6]
        column = BAIT_COLUMN[bait]
        if user[BAIT_INDEX[bait]] <= 0:
            bot.answer_callback_query(call.id, "❌ Наживка закончилась")
            return

        cursor.execute(f"UPDATE users SET {column}={column}-1, last_fish=? WHERE user_id=?", (now, uid))

        chance = RODS[user[3]]["chance"] + BAITS[bait]["bonus"]
        roll = random.randint(1, 100)

        if roll <= chance:
            fish = random.choice(FISH[user[4]])
            update_user(uid, "money", user[1] + fish[1])

            # квест
            if user[12] == fish[0]:
                update_user(uid, "quest_done", user[14] + 1)

            text = f"🐟 Ты поймал {fish[0]} (+{fish[1]}💰)"
        else:
            text = "❌ Рыба сорвалась"

        conn.commit()
        bot.answer_callback_query(call.id, text)

    # -------- КВЕСТЫ --------
    elif call.data == "quest":
        if user[14] >= user[13] and user[13] > 0:
            reward_money = random.randint(100, 300)
            update_user(uid, "money", user[1] + reward_money)
            cursor.execute("UPDATE users SET bait_worm=bait_worm+5 WHERE user_id=?", (uid,))
            new_quest(uid)
            text = f"✅ Квест выполнен!\nНаграда: {reward_money}💰 + 5 червей"
        else:
            text = f"📜 Квест\n🐟 Поймать: {user[12]}\n📊 Прогресс: {user[14]}/{user[13]}"
        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, reply_markup=main_menu())

    # -------- МАГАЗИН --------
    elif call.data == "shop":
        kb = types.InlineKeyboardMarkup()
        kb.add(types.InlineKeyboardButton("🎣 Удочки", callback_data="rods"))
        kb.add(types.InlineKeyboardButton("🎯 Наживки", callback_data="baits"))
        kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="back"))
        bot.edit_message_text("🛒 Магазин", call.message.chat.id, call.message.message_id, reply_markup=kb)

    # ===== УДОЧКИ =====
    elif call.data == "rods":
        kb = types.InlineKeyboardMarkup()
        for rid, rod in RODS.items():
            if rid > user[3]:
                kb.add(types.InlineKeyboardButton(f"{rod['name']} — {rod['price']}💰", callback_data=f"buyrod_{rid}"))
        kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="shop"))
        bot.edit_message_text("🎣 Магазин удочек", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data.startswith("buyrod_"):
        rid = int(call.data.split("_")[1])
        rod = RODS[rid]
        if user[1] >= rod["price"]:
            update_user(uid, "money", user[1] - rod["price"])
            update_user(uid, "rod", rid)
            bot.answer_callback_query(call.id, f"✅ Куплена удочка: {rod['name']}")
        else:
            bot.answer_callback_query(call.id, "❌ Не хватает денег")

    # ===== НАЖИВКИ =====
    elif call.data == "baits":
        kb = types.InlineKeyboardMarkup()
        for bait, data in BAITS.items():
            kb.add(types.InlineKeyboardButton(f"{bait} — {data['price']}💰", callback_data=f"buybait_{bait}"))
        kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="shop"))
        bot.edit_message_text("🎯 Магазин наживок", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data.startswith("buybait_"):
        bait = call.data.split("_")[1]
        if user[1] >= BAITS[bait]["price"]:
            update_user(uid, "money", user[1] - BAITS[bait]["price"])
            column = BAIT_COLUMN[bait]
            cursor.execute(f"UPDATE users SET {column}={column}+1 WHERE user_id=?", (uid,))
            conn.commit()
            bot.answer_callback_query(call.id, f"✅ Куплено: {bait}")
        else:
            bot.answer_callback_query(call.id, "❌ Не хватает денег")

    # ===== ЛОКАЦИИ =====
    elif call.data == "locations":
        kb = types.InlineKeyboardMarkup()
        for loc, price in LOCATIONS.items():
            kb.add(types.InlineKeyboardButton(f"{loc} — {price}💰", callback_data=f"loc_{loc}"))
        kb.add(types.InlineKeyboardButton("⬅ Назад", callback_data="back"))
        bot.edit_message_text("🗺 Локации", call.message.chat.id, call.message.message_id, reply_markup=kb)

    elif call.data.startswith("loc_"):
        loc = call.data.split("_")[1]
        if user[1] >= LOCATIONS[loc]:
            update_user(uid, "money", user[1] - LOCATIONS[loc])
            update_user(uid, "location", loc)
            bot.answer_callback_query(call.id, f"🗺 Ты на локации: {loc}")
        else:
            bot.answer_callback_query(call.id, "❌ Не хватает денег")

    elif call.data == "back":
        bot.edit_message_text("Главное меню", call.message.chat.id, call.message.message_id, reply_markup=main_menu())

# ================== RUN ==================
bot.polling(none_stop=True)

