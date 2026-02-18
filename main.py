import telebot
import os
import sqlite3
import threading
from flask import Flask
from telebot import types
from deep_translator import GoogleTranslator
from gtts import gTTS
import google.generativeai as genai
import time

# --- SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is alive!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_flask).start()

# --- SOZLAMALAR ---
TOKEN = "8171412076:AAGkTdkWzq5bVPLWUJI_K2Moo6RbbIwm4LU"
GEMINI_API_KEY = "AIzaSyBvayhxJDTp7OdaMjtkocoTzANdIukk6jE"
ADMIN_ID = 8249474846 

# Gemini modelini to'g'ri ulash
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Model nomi aniq 'models/gemini-1.5-flash' bo'lishi xatolikni oldini oladi
    ai_model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    print(f"Gemini init error: {e}")

bot = telebot.TeleBot(TOKEN)

# --- BAZA ---
def init_db():
    conn = sqlite3.connect("users_data.db", check_same_thread=False)
    conn.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    conn.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channel_id', '-1003334689234')")
    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channel_link', 'https://t.me/MindsetFortress')")
    conn.commit()
    conn.close()

init_db()
user_states = {}

# --- AI TEACHER LOGIKASI ---
def get_ai_reply(text):
    try:
        prompt = (
            "Sen professional ingliz tili o'qituvchisisan. Foydalanuvchi bilan inglizcha suhbatlash. "
            "Har bir javobing oxirida foydalanuvchining xatolarini o'zbekcha tushuntir. "
            "Javobni '---SPLIT---' bilan ajrat."
        )
        # Gemini javob berishini kutamiz
        response = ai_model.generate_content(f"{prompt}\nUser: {text}")
        return response.text
    except Exception as e:
        print(f"AI Error: {e}")
        return "I'm sorry, I have a connection issue. ---SPLIT--- Kechirasiz, Gemini API ulanishida xato: " + str(e)

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔄 Translate", "🔊 Pronounce", "👨‍🏫 AI Teacher")
    bot.send_message(message.chat.id, "🚀 Tayyorman!", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_msg(message):
    if message.text == "🔄 Translate":
        user_states[message.chat.id] = "translate"
        bot.send_message(message.chat.id, "📝 Matn yuboring:")
    elif message.text == "🔊 Pronounce":
        user_states[message.chat.id] = "pronounce"
        bot.send_message(message.chat.id, "🇬🇧 So'z yuboring:")
    elif message.text == "👨‍🏫 AI Teacher":
        user_states[message.chat.id] = "ai_teacher"
        bot.send_message(message.chat.id, "👨‍🏫 Chattingni boshladik!")
    else:
        state = user_states.get(message.chat.id)
        if state == "ai_teacher":
            bot.send_chat_action(message.chat.id, 'typing')
            res = get_ai_reply(message.text)
            if "---SPLIT---" in res:
                en, uz = res.split("---SPLIT---", 1)
                bot.reply_to(message, f"🇬🇧 {en.strip()}\n\n🇺🇿 {uz.strip()}")
            else: bot.reply_to(message, res)
        elif state == "translate":
            res = GoogleTranslator(source='auto', target='en').translate(message.text)
            bot.reply_to(message, res)
        elif state == "pronounce":
            f = f"{message.chat.id}.mp3"
            gTTS(text=message.text, lang='en').save(f)
            with open(f, "rb") as a: bot.send_voice(message.chat.id, a)
            os.remove(f)

if __name__ == "__main__":
    keep_alive()
    # Conflict xatosini kamaytirish uchun interval qo'shildi
    bot.infinity_polling(timeout=10, long_polling_timeout=5)
