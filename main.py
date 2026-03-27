import os, asyncio, sqlite3, yt_dlp, static_ffmpeg, uuid
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

static_ffmpeg.add_paths()
ua = UserAgent()

# إعدادات البوت الأساسية
TOKEN = os.getenv("BOT_TOKEN") or "8336468616:AAERqfaDgjMsbBx7wSkUwnDNeV7sKaFWtEA" 
ADMIN_ID =  8086158965

# --- [1] قاعدة البيانات (ثابتة بدون تغيير) ---
def init_db():
    conn = sqlite3.connect('pro_v_ultimate.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS links (id TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

def save_link(url):
    link_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect('pro_v_ultimate.db')
    conn.execute("INSERT INTO links (id, url) VALUES (?, ?)", (link_id, url))
    conn.commit()
    conn.close()
    return link_id

def get_link(link_id):
    conn = sqlite3.connect('pro_v_ultimate.db')
    row = conn.cursor().execute("SELECT url FROM links WHERE id=?", (link_id,)).fetchone()
    conn.close()
    return row[0] if row else None

init_db()

# --- [2] دالة يوتيوب المنفردة (لتجاوز الحظر) ---
async def youtube_worker(url, mode):
    opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if mode == 'v' else 'bestaudio/best',
        'nocheckcertificate': True,
        'geo_bypass': True,
        'http_headers': {'User-Agent': ua.random}
    }
    # إذا وضعت ملف cookies.txt بجانب الكود سيعمل يوتيوب 100%
    if os.path.exists('cookies.txt'):
        opts['cookiefile'] = 'cookies.txt'

    if mode == 'a':
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename)[0] + ".mp3" if mode == 'a' else filename

# --- [3] دالة المنصات الأخرى (فيس، تيك توك، إنستا) ---
async def social_worker(url, mode):
    opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'user_agent': ua.random,
        'extractor_args': {'instagram': {'check_headers': True}, 'tiktok': {'web_proxy': True}},
        'http_headers': {'Referer': 'https://www.google.com/'}
    }
    if mode == 'a':
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename)[0] + ".mp3" if mode == 'a' else filename

# --- [4] لوحة الإدمن والوظائف الإضافية ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    conn = sqlite3.connect('pro_v_ultimate.db')
    conn.execute("INSERT OR IGNORE INTO users (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
    await update.message.reply_text("🚀 البوت جاهز للتحميل من جميع المنصات!")

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID: return
    conn = sqlite3.connect('pro_v_ultimate.db')
    count = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    conn.close()
    keyboard = [[InlineKeyboardButton(f"📢 إذاعة لـ {count} مستخدم", callback_data="broadcast")]]
    await update.message.reply_text(f"🖥 لوحة الإدمن\n👤 المشتركين: {count}", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text

    # معالجة الإذاعة للإدمن
    if user_id == ADMIN_ID and context.user_data.get('waiting_broadcast'):
        conn = sqlite3.connect('pro_v_ultimate.db')
        users = [row[0] for row in conn.execute("SELECT user_id FROM users").fetchall()]
        conn.close()
        for uid in users:
            try: await context.bot.copy_message(chat_id=uid, from_chat_id=ADMIN_ID, message_id=update.message.message_id)
            except: continue
        context.user_data['waiting_broadcast'] = False
        await update.message.reply_text("✅ تمت الإذاعة بنجاح.")
        return

    if text and "http" in text:
        link_id = save_link(text)
        keyboard = [[InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{link_id}"), 
                     InlineKeyboardButton("🎵 صوت", callback_data=f"a|{link_id}")]]
        await update.message.reply_text("🎥 اختر ما تريد تحميله:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast":
        context.user_data['waiting_broadcast'] = True
        await query.message.reply_text("📥 أرسل الرسالة الآن للإذاعة.")
        return

    mode, link_id = query.data.split("|")
    url = get_link(link_id)
    if not os.path.exists('downloads'): os.makedirs('downloads')
    status_msg = await query.edit_message_text("⏳ جاري التحميل...")

    try:
        if any(x in url for x in ['youtube.com', 'youtu.be']):
            file_path = await youtube_worker(url, mode)
        else:
            file_path = await social_worker(url, mode)

        with open(file_path, 'rb') as f:
            if mode == 'v': await context.bot.send_video(chat_id=update.effective_chat.id, video=f)
            else: await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f)
        
        os.remove(file_path)
        await status_msg.delete()
    except Exception as e:
        await query.message.reply_text(f"⚠️ فشل التحميل: {str(e)[:50]}...")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    # حل مشكلة الـ Conflict بشكل نهائي
    application.run_polling(drop_pending_updates=True)
