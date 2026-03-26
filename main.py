import os
import asyncio
import sqlite3
import yt_dlp
import static_ffmpeg
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# تفعيل FFmpeg بشكل صحيح لحل مشاكل الدمج
static_ffmpeg.add_paths()
ua = UserAgent()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8086158965 # معرفك الخاص

# --- إعداد قاعدة البيانات لحفظ المستخدمين ---
def init_db():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def get_all_users():
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute("SELECT user_id FROM users")
    users = [row[0] for row in c.fetchall()]
    conn.close()
    return users

init_db()

# --- إعدادات تحميل فيسبوك وإنستغرام ---
def get_ydl_opts(mode):
    opts = {
        'format': 'bestvideo+bestaudio/best' if mode == 'v' else 'bestaudio/best',
        'outtmpl': 'file.%(ext)s',
        'prefer_ffmpeg': True,
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        'socket_timeout': 20, # منع الكراش في الروابط البطيئة
        'extractor_args': {
            'facebook': {'force_get_url': True}, # حل مشكلة فيسبوك
            'instagram': {'check_headers': True}
        },
        'http_headers': {'User-Agent': ua.random, 'Referer': 'https://www.facebook.com/'}
    }
    if mode == 'a':
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
    return opts

# --- أوامر الإدمن ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    await update.message.reply_text("أهلاً بك في بوت التحميل المطور! 🚀\nأرسل رابط فيديو للبدء.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    users_count = len(get_all_users())
    keyboard = [
        [InlineKeyboardButton("📢 إذاعة عامة", callback_data="broadcast")],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats")]
    ]
    await update.message.reply_text(f"🖥 **لوحة تحكم علاوي**\n\nعدد المشتركين: {users_count}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    
    # ميزة الإذاعة: إذا كان الإدمن يرسل رسالة بعد الضغط على زر الإذاعة
    if user_id == ADMIN_ID and context.user_data.get('waiting_broadcast'):
        users = get_all_users()
        sent = 0
        for uid in users:
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=ADMIN_ID, message_id=update.message.message_id)
                sent += 1
            except: pass
        context.user_data['waiting_broadcast'] = False
        await update.message.reply_text(f"✅ تم إرسال الإذاعة إلى {sent} مستخدم.")
        return

    url = update.message.text
    if "http" in url:
        clean_url = url.split('?')[0] if 'instagram.com' in url else url
        keyboard = [[InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{clean_url}"), InlineKeyboardButton("🎵 صوت", callback_data=f"a|{clean_url}")]]
        await update.message.reply_text("📥 اختر الصيغة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast":
        context.user_data['waiting_broadcast'] = True
        await query.message.reply_text("📥 أرسل الآن الرسالة (نص، صورة، فيديو) التي تريد إذاعتها لكل المستخدمين.")
        return
    
    if query.data == "stats":
        await query.message.reply_text(f"📊 إجمالي المستخدمين في القاعدة: {len(get_all_users())}")
        return

    mode, url = query.data.split("|")
    status_msg = await query.edit_message_text("⏳ جاري التحميل... يرجى الانتظار.")

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(mode)) as ydl:
            # تشغيل في الخلفية لمنع توقف البوت
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            if mode == 'a': filename = filename.rsplit('.', 1)[0] + ".mp3"

        with open(filename, 'rb') as f:
            if mode == 'v': await context.bot.send_video(chat_id=update.effective_chat.id, video=f)
            else: await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f)
        
        os.remove(filename)
        await status_msg.delete()
    except:
        await query.message.reply_text("⚠️ فشل التحميل. قد يكون الرابط خاصاً أو محمياً.")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.TEXT | filters.PHOTO | filters.VIDEO & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling(drop_pending_updates=True)
