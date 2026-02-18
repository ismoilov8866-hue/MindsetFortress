import telebot
import os
import sqlite3
import threading
from flask import Flask
from telebot import types
from deep_translator import GoogleTranslator
from gtts import gTTS
import google.generativeai as genai

# --- RENDER/REPLIT WEB SERVER ---
app = Flask('')
@app.route('/')
def home(): return "Bot is active with AI Teacher!"

def run_flask():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

def keep_alive():
    threading.Thread(target=run_flask).start()

# --- SOZLAMALAR ---
TOKEN = "8171412076:AAGkTdkWzq5bVPLWUJI_K2Moo6RbbIwm4LU"
# Diqqat: Gemini API kalitini https://aistudio.google.com/ dan oling
GEMINI_API_KEY = "BU_YERGA_GEMINI_API_KEY_QOYING"

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

ADMIN_ID = 8249474846 
bot = telebot.TeleBot(TOKEN)

# --- BAZA ---
def init_db():
    conn = sqlite3.connect("users_data.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)")
    cursor.execute("CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT)")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channel_id', '-1003334689234')")
    cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('channel_link', 'https://t.me/MindsetFortress')")
    conn.commit()
    conn.close()

def get_setting(key):
    conn = sqlite3.connect("users_data.db")
    res = conn.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
    conn.close()
    return res[0] if res else None

init_db()
user_states = {}

# --- OBUNA TEKSHIRUV ---
def check_sub(user_id):
    channel_id = get_setting('channel_id')
    if not channel_id or channel_id == "0": return True
    try:
        status = bot.get_chat_member(chat_id=channel_id, user_id=user_id).status
        return status in ['member', 'administrator', 'creator']
    except: return True 

# --- AI TEACHER FUNKSIYASI ---
def get_ai_reply(text):
    try:
        prompt = f"Sen professional ingliz tili o'qituvchisisan. Foydalanuvchi bilan inglizcha suhbatlash va oxirida uning xatolarini o'zbekcha tushuntirib ber. Javobni '---SPLIT---' bilan ajrat: 1-qism inglizcha javob, 2-qism o'zbekcha tahlil. Foydalanuvchi xabari: {text}"
        response = model.generate_content(prompt)
        return response.text
    except:
        return "I'm sorry, I'm having a connection issue. ---SPLIT--- Kechirasiz, ulanishda xatolik yuz berdi."

# --- HANDLERS ---
@bot.message_handler(commands=['start'])
def start(message):
    conn = sqlite3.connect("users_data.db")
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (message.chat.id,))
    conn.commit()
    conn.close()
    
    if not check_sub(message.chat.id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Obuna bo'lish", url=get_setting('channel_link')))
        bot.send_message(message.chat.id, "⚠️ Botdan foydalanish uchun kanalga a'zo bo'ling!", reply_markup=markup)
        return
        
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.add("🔄 Translate", "🔊 Pronounce")
    markup.add("👨‍🏫 AI Teacher")
    if message.chat.id == ADMIN_ID:
        markup.add("📊 Statistika")
    bot.send_message(message.chat.id, "🚀 Tanlang:", reply_markup=markup)

@bot.message_handler(func=lambda m: True)
def handle_text(message):
    if not check_sub(message.chat.id): return

    if message.text == "🔄 Translate":
        user_states[message.chat.id] = "translate"
        bot.send_message(message.chat.id, "📝 Matn yuboring:")
    elif message.text == "🔊 Pronounce":
        user_states[message.chat.id] = "pronounce"
        bot.send_message(message.chat.id, "🇬🇧 So'z yuboring:")
    elif message.text == "👨‍🏫 AI Teacher":
        user_states[message.chat.id] = "ai_teacher"
        bot.send_message(message.chat.id, "👨‍🏫 Men tayyorman! Inglizcha yozing, men javob beraman va xatolaringizni tahlil qilaman.")
    
    else:
        state = user_states.get(message.chat.id)
        if state == "translate":
            res = GoogleTranslator(source='auto', target='en').translate(message.text)
            bot.reply_to(message, f"✅ EN: {res}")
            
        elif state == "pronounce":
            fname = f"p_{message.chat.id}.mp3"
            gTTS(text=message.text, lang='en').save(fname)
            with open(fname, "rb") as a: bot.send_voice(message.chat.id, a)
            os.remove(fname)
            
        elif state == "ai_teacher":
            bot.send_chat_action(message.chat.id, 'typing')
            full_reply = get_ai_reply(message.text)
            if "---SPLIT---" in full_reply:
                en, uz = full_reply.split("---SPLIT---", 1)
                bot.reply_to(message, f"🇬🇧 **Teacher:**\n{en.strip()}\n\n🇺🇿 **Tahlil:**\n{uz.strip()}", parse_mode="Markdown")
            else:
                bot.reply_to(message, full_reply)

if __name__ == "__main__":
    keep_alive()
    bot.infinity_polling()
