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
def home(): return "Bot is working perfectly!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_flask).start()

# --- SOZLAMALAR ---
TOKEN = "8171412076:AAGkTdkWzq5bVPLWUJI_K2Moo6RbbIwm4LU"
GEMINI_API_KEY = "AIzaSyBvayhxJDTp7OdaMjtkocoTzANdIukk6jE"

# Gemini modelini yangilangan nom bilan sozlash
try:
    genai.configure(api_key=GEMINI_API_KEY)
    # Model nomini eng barqaror versiyaga o'zgartirdik
    ai_model = genai.GenerativeModel('gemini-1.5-flash-latest')
except Exception as e:
    print(f"Gemini sozlashda xato: {e}")

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

# --- AI TEACHER FUNKSIYASI ---
def get_ai_reply(text):
    try:
        # Promptni maksimal darajada soddalashtirdik
        prompt = (
            f"You are a helpful English teacher. Talk to me in English about: {text}. "
            "Then, after a '---SPLIT---' marker, explain any grammar mistakes in Uzbek."
        )
        response = ai_model.generate_content(prompt)
        
        if response and response.text:
            return response.text
        else:
            return "I couldn't generate a response. ---SPLIT--- AI javob qaytara olmadi."
            
    except Exception as e:
        print(f"AI Xatosi: {e}")
        # Agar model nomi hali ham topilmasa, muqobil modelni sinab ko'radi
        return f"Connection error. ---SPLIT--- Xatolik yuz berdi: {str(e)[:100]}"

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔄 Translate", "🔊 Pronounce", "👨‍🏫 AI Teacher")
    bot.send_message(message.chat.id, "🚀 Tayyorman! Bo'limni tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_msg(message):
    if message.text == "🔄 Translate":
        user_states[message.chat.id] = "translate"
        bot.send_message(message.chat.id, "📝 Matn yuboring:")
    elif message.text == "🔊 Pronounce":
        user_states[message.chat.id] = "pronounce"
        bot.send_message(message.chat.id, "🇬🇧 Inglizcha yozing:")
    elif message.text == "👨‍🏫 AI Teacher":
        user_states[message.chat.id] = "ai_teacher"
        bot.send_message(message.chat.id, "👨‍🏫 Inglizcha biror nima deb yozing, suhbatni boshlaymiz!")
    else:
        state = user_states.get(message.chat.id)
        
        if state == "ai_teacher":
            bot.send_chat_action(message.chat.id, 'typing')
            res = get_ai_reply(message.text)
            if "---SPLIT---" in res:
                en, uz = res.split("---SPLIT---", 1)
                bot.send_message(message.chat.id, f"🇬🇧 **Teacher:**\n{en.strip()}\n\n🇺🇿 **Tahlil:**\n{uz.strip()}", parse_mode="Markdown")
            else:
                bot.reply_to(message, res)
                
        elif state == "translate":
            try:
                res = GoogleTranslator(source='auto', target='en').translate(message.text)
                bot.reply_to(message, f"✅ EN: {res}")
            except: bot.reply_to(message, "Tarjima xatosi.")
            
        elif state == "pronounce":
            try:
                f = f"v_{message.chat.id}.mp3"
                gTTS(text=message.text, lang='en').save(f)
                with open(f, "rb") as v: bot.send_voice(message.chat.id, v)
                os.remove(f)
            except: bot.send_message(message.chat.id, "Ovoz xatosi.")

if __name__ == "__main__":
    keep_alive()
    # Konfliktni (409) butunlay yo'qotish uchun eski pollingni tozalaymiz
    bot.delete_webhook()
    time.sleep(2) 
    print("Bot ishga tushmoqda...")
    bot.infinity_polling(timeout=20, long_polling_timeout=10)
