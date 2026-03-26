import os, asyncio, sqlite3, yt_dlp, static_ffmpeg, uuid
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# تأمين مسارات المعالجة لضمان تحويل الصوت
static_ffmpeg.add_paths()
ua = UserAgent()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID =  8086158965

# --- إدارة البيانات ---
def init_db():
    conn = sqlite3.connect('bot_pro.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS links (id TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

def add_user(user_id):
    conn = sqlite3.connect('bot_pro.db')
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()

def save_link(url):
    link_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect('bot_pro.db')
    conn.execute("INSERT INTO links (id, url) VALUES (?, ?)", (link_id, url))
    conn.commit()
    conn.close()
    return link_id

def get_link(link_id):
    conn = sqlite3.connect('bot_pro.db')
    row = conn.cursor().execute("SELECT url FROM links WHERE id=?", (link_id,)).fetchone()
    conn.close()
    return row[0] if row else None

init_db()

# --- إعدادات التحميل المحسنة لفيسبوك وإنستا ---
def get_ydl_opts(mode):
    opts = {
        'outtmpl': 'file.%(ext)s',
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': ua.random,
        'format': 'bestaudio/best' if mode == 'a' else 'bestvideo+bestaudio/best',
        'extractor_args': {'facebook': {'force_get_url': True}, 'instagram': {'check_headers': True}},
        'http_headers': {'Referer': 'https://www.facebook.com/'}
    }
    if mode == 'a':
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    return opts

# --- الأوامر والتعامل مع الرسائل ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    add_user(update.effective_user.id)
    await update.message.reply_text("👋 أهلاً بك! تم تصحيح الكود وتحديث النظام.\nأرسل الرابط الآن.")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    keyboard = [[InlineKeyboardButton("📢 إذاعة عامة", callback_data="broadcast")]]
    await update.message.reply_text("🖥 لوحة التحكم:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    add_user(user_id)
    
    # تصحيح ميزة الإذاعة العامة
    if user_id == ADMIN_ID and context.user_data.get('waiting_broadcast'):
        conn = sqlite3.connect('bot_pro.db')
        users = [row[0] for row in conn.execute("SELECT user_id FROM users").fetchall()]
        conn.close()
        for uid in users:
            try:
                await context.bot.copy_message(chat_id=uid, from_chat_id=ADMIN_ID, message_id=update.message.message_id)
            except:
                continue
        context.user_data['waiting_broadcast'] = False
        await update.message.reply_text("✅ تم إرسال الإذاعة للجميع.")
        return

    url = update.message.text
    if url and "http" in url:
        link_id = save_link(url)
        keyboard = [[
            InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{link_id}"),
            InlineKeyboardButton("🎵 صوت MP3", callback_data=f"a|{link_id}")
        ]]
        await update.message.reply_text("⚙️ اختر الصيغة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast":
        context.user_data['waiting_broadcast'] = True
        await query.message.reply_text("📥 أرسل الرسالة التي تريد إذاعتها الآن.")
        return

    mode, link_id = query.data.split("|")
    url = get_link(link_id)
    if not url:
        await query.message.reply_text("⚠️ الرابط منتهي، أرسله مجدداً.")
        return

    status_msg = await query.edit_message_text("⏳ جاري التحميل والمعالجة...")

    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(get_ydl_opts(mode)) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            if mode == 'a': filename = filename.rsplit('.', 1)[0] + ".mp3"

        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                if mode == 'v':
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=f)
                else:
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f)
            os.remove(filename)
            await status_msg.delete()
        else:
            await query.message.reply_text("❌ لم يتم العثور على الملف.")
    except Exception as e:
        print(f"Error: {e}")
        await query.message.reply_text("⚠️ فشل التحميل. تأكد أن الرابط عام.")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling(drop_pending_updates=True)
    
