import os, asyncio, sqlite3, yt_dlp, static_ffmpeg, uuid
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

static_ffmpeg.add_paths()
ua = UserAgent()

# ضع التوكن هنا مباشرة إذا لم يعمل من إعدادات Railway لضمان التشغيل
TOKEN = os.getenv("BOT_TOKEN") or "8336468616:AAH14XW8LAPfmrne5SX2P7IKGL19s_honJc" 
ADMIN_ID =  8086158965

def init_db():
    conn = sqlite3.connect('pro_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS links (id TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

def save_link(url):
    link_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect('pro_data.db')
    conn.execute("INSERT INTO links (id, url) VALUES (?, ?)", (link_id, url))
    conn.commit()
    conn.close()
    return link_id

def get_link(link_id):
    conn = sqlite3.connect('pro_data.db')
    row = conn.cursor().execute("SELECT url FROM links WHERE id=?", (link_id,)).fetchone()
    conn.close()
    return row[0] if row else None

init_db()

def get_ydl_opts(mode):
    # إعدادات محسنة لفيسبوك وإنستغرام لضمان سحب الفيديو
    opts = {
        'outtmpl': 'file.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True,
        'user_agent': ua.random,
        'format': 'bestvideo+bestaudio/best' if mode == 'v' else 'bestaudio/best',
        'extractor_args': {
            'facebook': {'force_get_url': True},
            'instagram': {'check_headers': True}
        },
        'http_headers': {
            'Referer': 'https://www.instagram.com/',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    }
    if mode == 'a':
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    return opts

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 أهلاً بك! تم تفعيل لوحة الإدمن وإصلاح تحميل إنستغرام.")

# --- تفعيل لوحة الإدمن ---
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    keyboard = [[InlineKeyboardButton("📢 إرسال إذاعة", callback_data="broadcast")]]
    await update.message.reply_text("🖥 لوحة تحكم الإدمن:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text
    
    # معالج الإذاعة
    if user_id == ADMIN_ID and context.user_data.get('waiting_broadcast'):
        conn = sqlite3.connect('pro_data.db')
        users = [row[0] for row in conn.execute("SELECT user_id FROM users").fetchall()]
        conn.close()
        for uid in users:
            try: await context.bot.copy_message(chat_id=uid, from_chat_id=ADMIN_ID, message_id=update.message.message_id)
            except: continue
        context.user_data['waiting_broadcast'] = False
        await update.message.reply_text("✅ تم الإرسال للجميع.")
        return

    if text and "http" in text:
        link_id = save_link(text)
        keyboard = [[
            InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{link_id}"),
            InlineKeyboardButton("🎵 صوت MP3", callback_data=f"a|{link_id}")
        ]]
        await update.message.reply_text("📥 اختر النوع المطلوب تحميله:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast":
        context.user_data['waiting_broadcast'] = True
        await query.message.reply_text("📥 أرسل الرسالة (نص، صورة، فيديو) لإذاعتها.")
        return

    mode, link_id = query.data.split("|")
    url = get_link(link_id)
    status_msg = await query.edit_message_text("⏳ جاري التحميل والمعالجة... قد يستغرق فيديو إنستا وقتاً أطول.")

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(mode)) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            if mode == 'a': filename = filename.rsplit('.', 1)[0] + ".mp3"

        with open(filename, 'rb') as f:
            if mode == 'v': await context.bot.send_video(chat_id=update.effective_chat.id, video=f)
            else: await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f)
        
        os.remove(filename)
        await status_msg.delete()
    except Exception as e:
        await query.message.reply_text(f"⚠️ فشل التحميل. إنستغرام يطلب كوكيز أحياناً للروابط المحمية.")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling(drop_pending_updates=True)
