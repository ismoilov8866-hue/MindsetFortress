import telebot
import os
import sqlite3
import threading
from flask import Flask
from telebot import types
from deep_translator import GoogleTranslator
from gtts import gTTS
import google.generativeai as genai

# --- RENDER/REPLIT UCHUN WEB SERVER (Keep Alive) ---
app = Flask('')

@app.route('/')
def home():
    return "Bot 24/7 rejimida muvaffaqiyatli ishlayapti!"

def run_flask():
    # Render avtomatik beradigan portni oladi
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_flask).start()

# --- ASOSIY SOZLAMALAR ---
TOKEN = "8171412076:AAGkTdkWzq5bVPLWUJI_K2Moo6RbbIwm4LU"
GEMINI_API_KEY = "AIzaSyBvayhxJDTp7OdaMjtkocoTzANdIukk6jE"
ADMIN_ID = 8249474846 

# Gemini AI sozlamalari
genai.configure(api_key=GEMINI_API_KEY)
ai_model = genai.GenerativeModel('gemini-1.5-flash')

bot = telebot.TeleBot(TOKEN)

# --- MA'LUMOTLAR BAZASI (SQLite) ---
def init_db():
    conn = sqlite3.connect("users_data.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channel_id', '-1003334689234')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channel_link', 'https://t.me/MindsetFortress')")
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect("users_data.db", check_same_thread=False)
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect("users_data.db", check_same_thread=False)
    res = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return res[0] if res else None

def update_setting(key, value):
    conn = sqlite3.connect("users_data.db", check_same_thread=False)
    conn.execute("UPDATE settings SET value=? WHERE key=?", (value, key))
    conn.commit()
    conn.close()

init_db()
user_states = {}

# --- MAJBURIY OBUNA TEKSHIRUVI ---
def check_sub(user_id):
    channel_id = get_setting('channel_id')
    if not channel_id or channel_id == "0": 
        return True
    try:
        status = bot.get_chat_member(chat_id=channel_id, user_id=user_id).status
        return status in ['member', 'administrator', 'creator']
    except:
        return True 

# --- AI TEACHER FUNKSIYASI ---
def get_ai_reply(text):
    try:
        prompt = (
            "Sen professional ingliz tili o'qituvchisisan. Foydalanuvchi bilan inglizcha suhbatlash. "
            "Har bir javobing oxirida foydalanuvchining xatolarini (agar bo'lsa) o'zbekcha tushuntirib ber. "
            "Javobingni aniq '---SPLIT---' belgisi bilan ajrat. "
            "Format: [Inglizcha javob] ---SPLIT--- [O'zbekcha tahlil]. "
            f"Foydalanuvchi xabari: {text}"
        )
        response = ai_model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return "I'm sorry, I'm having trouble thinking right now. ---SPLIT--- Kechirasiz, AI ulanishida xatolik yuz berdi."

# --- HANDLERS ---

@bot.message_handler(commands=['start'])
def start(message):
    add_user(message.chat.id)
    
    if not check_sub(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Obuna bo'lish", url=get_setting('channel_link')))
        bot.send_message(message.chat.id, "⚠️ Botdan foydalanish uchun kanalimizga obuna bo'ling!", reply_markup=markup)
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔄 Translate", "🔊 Pronounce")
    markup.add("👨‍🏫 AI Teacher")
    if message.chat.id == ADMIN_ID:
        markup.add("📊 Statistika", "📢 Reklama")
        markup.add("⚙️ Kanal Sozlamalari")
        
    bot.send_message(message.chat.id, "🚀 Xush kelibsiz! Kerakli bo'limni tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_all(message):
    # Majburiy obuna tekshiruvi (Admin emaslar uchun)
    if message.chat.id != ADMIN_ID and not check_sub(message.chat.id):
        bot.send_message(message.chat.id, "⚠️ Avval kanalga a'zo bo'ling!")
        return

    # --- ADMIN BOSHQARUVI ---
    if message.text == "📊 Statistika" and message.chat.id == ADMIN_ID:
        conn = sqlite3.connect("users_data.db")
        count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        bot.send_message(ADMIN_ID, f"👥 Jami foydalanuvchilar: {count} ta")

    elif message.text == "📢 Reklama" and message.chat.id == ADMIN_ID:
        user_states[ADMIN_ID] = "sending_ad"
        bot.send_message(ADMIN_ID, "Reklama xabarini yuboring (Matn, Rasm, Video yoki Ovozli xabar):")

    elif message.text == "⚙️ Kanal Sozlamalari" and message.chat.id == ADMIN_ID:
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("🆔 Kanal ID o'zgartirish", callback_data="set_id"))
        markup.add(types.InlineKeyboardButton("🔗 Kanal Linkini o'zgartirish", callback_data="set_link"))
        markup.add(types.InlineKeyboardButton("🚫 Obunani o'chirish", callback_data="disable_sub"))
        bot.send_message(ADMIN_ID, f"Hozirgi kanal ID: {get_setting('channel_id')}\nLink: {get_setting('channel_link')}", reply_markup=markup)

    # --- ASOSIY BO'LIMLAR ---
    elif message.text == "🔄 Translate":
        user_states[message.chat.id] = "translate"
        bot.send_message(message.chat.id, "📝 Tarjima uchun matn yuboring (UZ ↔️ EN):")

    elif message.text == "🔊 Pronounce":
        user_states[message.chat.id] = "pronounce"
        bot.send_message(message.chat.id, "🇬🇧 Talaffuzini eshitish uchun inglizcha so'z yuboring:")

    elif message.text == "👨‍🏫 AI Teacher":
        user_states[message.chat.id] = "ai_teacher"
        bot.send_message(message.chat.id, "👨‍🏫 Tayyorman! Inglizcha suhbatni boshlashimiz mumkin. Nima haqida gaplashamiz?")

    # --- STATES (Holatlar) ---
    else:
        state = user_states.get(message.chat.id)
        
        if state == "translate":
            try:
                text = message.text
                translated = GoogleTranslator(source='auto', target='en').translate(text)
                # Tilni aniqlash mantig'i
                if translated.lower().strip() == text.lower().strip():
                    res = GoogleTranslator(source='auto', target='uz').translate(text)
                    bot.reply_to(message, f"🇺🇿 **O'zbekcha:**\n{res}")
                else:
                    bot.reply_to(message, f"🇬🇧 **English:**\n{translated}")
            except:
                bot.reply_to(message, "⚠️ Tarjimada xatolik yuz berdi.")

        elif state == "pronounce":
            try:
                audio_file = f"audio_{message.chat.id}.mp3"
                tts = gTTS(text=message.text, lang='en')
                tts.save(audio_file)
                with open(audio_file, "rb") as audio:
                    bot.send_voice(message.chat.id, audio)
                os.remove(audio_file)
            except:
                bot.send_message(message.chat.id, "⚠️ Ovoz yaratishda xato.")

        elif state == "ai_teacher":
            bot.send_chat_action(message.chat.id, 'typing')
            full_reply = get_ai_reply(message.text)
            if "---SPLIT---" in full_reply:
                en, uz = full_reply.split("---SPLIT---", 1)
                bot.reply_to(message, f"🇬🇧 **Teacher:**\n{en.strip()}\n\n🇺🇿 **Tahlil:**\n{uz.strip()}", parse_mode="Markdown")
            else:
                bot.reply_to(message, full_reply)

        elif state == "sending_ad" and message.chat.id == ADMIN_ID:
            conn = sqlite3.connect("users_data.db")
            users = conn.execute("SELECT user_id FROM users").fetchall()
            count = 0
            for u in users:
                try:
                    bot.copy_message(u[0], message.chat.id, message.message_id)
                    count += 1
                except: pass
            bot.send_message(ADMIN_ID, f"✅ Reklama {count} foydalanuvchiga yuborildi.")
            user_states[ADMIN_ID] = None

        elif state == "wait_cid":
            update_setting('channel_id', message.text)
            bot.send_message(ADMIN_ID, "✅ Kanal ID yangilandi.")
            user_states[ADMIN_ID] = None

        elif state == "wait_clink":
            update_setting('channel_link', message.text)
            bot.send_message(ADMIN_ID, "✅ Kanal linki yangilandi.")
            user_states[ADMIN_ID] = None

# --- CALLBACKS (Inline Tugmalar) ---
@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    if call.data == "set_id":
        user_states[ADMIN_ID] = "wait_cid"
        bot.send_message(ADMIN_ID, "Yangi Kanal ID sini yuboring (masalan: -100...):")
    elif call.data == "set_link":
        user_states[ADMIN_ID] = "wait_clink"
        bot.send_message(ADMIN_ID, "Yangi Kanal linkini yuboring:")
    elif call.data == "disable_sub":
        update_setting('channel_id', '0')
        bot.send_message(ADMIN_ID, "✅ Majburiy obuna bekor qilindi.")

# --- ISHGA TUSHIRISH ---
if __name__ == "__main__":
    init_db()
    keep_alive()
    print("Bot muvaffaqiyatli ishga tushdi!")
    bot.infinity_polling()
