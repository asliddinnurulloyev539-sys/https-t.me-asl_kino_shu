import os
import json
import telebot
import google.generativeai as genai

# Kalitlarni olish
TELEGRAM_TOKEN = os.environ.get('TELEGRAM_TOKEN')
GEMINI_API_KEY = os.environ.get('GEMINI_API_KEY')
ADMIN_ID = int(os.environ.get('ADMIN_ID', 0))

# SI va Botni sozlash
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash', system_instruction="Siz aqlli yordamchisiz. Har doim faqat o'zbek tilida javob bering.")
bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Ma'lumotlar fayllari
MOVIES_FILE = 'movies.json'
USERS_FILE = 'users.json'

def load_data(filename):
    if os.path.exists(filename):
        with open(filename, 'r') as f:
            return json.load(f)
    return {} if filename == MOVIES_FILE else []

def save_data(filename, data):
    with open(filename, 'w') as f:
        json.dump(data, f)

# Foydalanuvchini bazaga qo'shish
def add_user(user_id):
    users = load_data(USERS_FILE)
    if user_id not in users:
        users.append(user_id)
        save_data(USERS_FILE, users)

# /start buyrug'i
@bot.message_handler(commands=['start'])
def send_welcome(message):
    add_user(message.from_user.id)
    bot.reply_to(message, "Salom! Men siz yaratgan Sun'iy Intellekt botiman. Savol bering yoki kino kodini kiriting!")

# /stat buyrug'i (Faqat Admin uchun)
@bot.message_handler(commands=['stat'])
def show_stats(message):
    if message.from_user.id == ADMIN_ID:
        users = load_data(USERS_FILE)
        bot.reply_to(message, f"📊 Jami foydalanuvchilar soni: {len(users)} ta")

# /send buyrug'i (Reklama yuborish - Faqat Admin uchun)
@bot.message_handler(commands=['send'])
def broadcast_ad(message):
    if message.from_user.id == ADMIN_ID and message.reply_to_message:
        users = load_data(USERS_FILE)
        rep_msg = message.reply_to_message
        success, failed = 0, 0
        
        bot.reply_to(message, "📢 Reklama tarqatish boshlandi...")
        
        for u_id in users:
            try:
                bot.copy_message(chat_id=u_id, from_chat_id=rep_msg.chat.id, message_id=rep_msg.message_id)
                success += 1
            except:
                failed += 1
                
        bot.reply_to(message, f"✅ Reklama yakunlandi!\n\nYetkazildi: {success} ta\nBloklaganlar: {failed} ta")

# Kinolarni admin tomonidan qo'shish
@bot.message_handler(content_types=['video'], func=lambda m: m.caption and m.caption.startswith('/add '))
def add_movie(message):
    if message.from_user.id == ADMIN_ID:
        code = message.caption.split('/add ')[1].strip()
        movies = load_data(MOVIES_FILE)
        movies[code] = message.video.file_id
        save_data(MOVIES_FILE, movies)
        bot.reply_to(message, f"🎬 Kino muvaffaqiyatli saqlandi. Kodi: {code}")

# Matnli va raqamli xabarlarni tekshirish
@bot.message_handler(func=lambda message: True)
def handle_all(message):
    add_user(message.from_user.id)
    text = message.text.strip()
    
    # Agar faqat raqamlardan iborat bo'lsa (Kino qidirish)
    if text.isdigit():
        movies = load_data(MOVIES_FILE)
        if text in movies:
            bot.send_video(message.chat.id, movies[text], caption=f"🎬 Mana siz qidirgan kino! (Kod: {text})")
        else:
            bot.reply_to(message, "😔 Afsuski, bu kod bilan hech qanday kino topilmadi.")
    else:
        # Sun'iy intellekt javobi
        try:
            response = model.generate_content(text)
            bot.reply_to(message, response.text)
        except:
            bot.reply_to(message, "Xatolik yuz berdi. Gemini tizimi band bo'lishi mumkin.")

# Ovozli xabarlar
@bot.message_handler(content_types=['voice'])
def handle_voice(message):
    add_user(message.from_user.id)
    try:
        file_info = bot.get_file(message.voice.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        response = model.generate_content([{"mime_type": "audio/ogg", "data": downloaded_file}])
        bot.reply_to(message, response.text)
    except:
        bot.reply_to(message, "Ovozni tushunishda xatolik bo'ldi.")

print("Bot reklama tizimi bilan muvaffaqiyatli ishga tushdi!")
bot.infinity_polling()
