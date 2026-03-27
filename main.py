import os, asyncio, sqlite3, yt_dlp, static_ffmpeg, uuid
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

static_ffmpeg.add_paths()
ua = UserAgent()

TOKEN = os.getenv("BOT_TOKEN") or "ضـع_تـوكـن_بـوتـك_هـنـا" 
ADMIN_ID = 8086158965

# --- قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('pro_vfinal.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS links (id TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

def save_link(url):
    link_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect('pro_vfinal.db')
    conn.execute("INSERT INTO links (id, url) VALUES (?, ?)", (link_id, url))
    conn.commit()
    conn.close()
    return link_id

def get_link(link_id):
    conn = sqlite3.connect('pro_vfinal.db')
    row = conn.cursor().execute("SELECT url FROM links WHERE id=?", (link_id,)).fetchone()
    conn.close()
    return row[0] if row else None

init_db()

# --- إعدادات التحميل المحسنة ليوتيوب والمنصات الأخرى ---
def get_ydl_opts(mode, url):
    is_youtube = any(x in url for x in ['youtube.com', 'youtu.be'])
    
    opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s', # تحديد مجلد للتحميل لتجنب تضارب الملفات
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'user_agent': ua.random,
        # تحسين جودة يوتيوب (فيديو + صوت)
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if mode == 'v' else 'bestaudio/best',
    }

    if not is_youtube:
        opts['extractor_args'] = {
            'facebook': {'force_get_url': True},
            'instagram': {'check_headers': True}
        }
        opts['http_headers'] = {
            'Referer': 'https://www.google.com/',
            'Accept-Language': 'en-US,en;q=0.9'
        }
    
    if mode == 'a':
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    return opts

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('pro_vfinal.db')
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("✅ تم تحديث البوت ليدعم يوتيوب بالكامل (Shorts & Videos)!")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    conn = sqlite3.connect('pro_vfinal.db')
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    keyboard = [[InlineKeyboardButton(f"📢 إذاعة", callback_data="broadcast")]]
    await update.message.reply_text(f"🖥 لوحة الإدمن | المشتركين: {count}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    if user_id == ADMIN_ID and context.user_data.get('waiting_broadcast'):
        conn = sqlite3.connect('pro_vfinal.db')
        users = [row[0] for row in conn.execute("SELECT user_id FROM users").fetchall()]
        conn.close()
        for uid in users:
            try: await context.bot.copy_message(chat_id=uid, from_chat_id=ADMIN_ID, message_id=update.message.message_id)
            except: continue
        context.user_data['waiting_broadcast'] = False
        await update.message.reply_text("✅ تم الإرسال.")
        return

    if text and "http" in text:
        link_id = save_link(text)
        keyboard = [[
            InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{link_id}"),
            InlineKeyboardButton("🎵 صوت MP3", callback_data=f"a|{link_id}")
        ]]
        await update.message.reply_text("🎥 اختر النوع:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast":
        context.user_data['waiting_broadcast'] = True
        await query.message.reply_text("📥 أرسل الإذاعة.")
        return

    mode, link_id = query.data.split("|")
    url = get_link(link_id)
    status_msg = await query.edit_message_text("⏳ جاري التحميل من يوتيوب...")

    if not os.path.exists('downloads'): os.makedirs('downloads')

    try:
        opts = get_ydl_opts(mode, url)
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            # تصحيح الامتداد في حالة تحويل الصوت
            if mode == 'a':
                filename = os.path.splitext(filename)[0] + ".mp3"

        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                if mode == 'v': await context.bot.send_video(chat_id=update.effective_chat.id, video=f)
                else: await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f)
            os.remove(filename)
            await status_msg.delete()
    except Exception as e:
        await query.message.reply_text("⚠️ فشل التحميل. قد يكون الرابط محمياً بموجب حقوق الطبع أو خاصاً.")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    # حل مشكلة التضارب (Conflict) في Railway
    application.run_polling(drop_pending_updates=True)
