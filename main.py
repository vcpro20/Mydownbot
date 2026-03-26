import os, asyncio, sqlite3, yt_dlp, static_ffmpeg, uuid
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# تفعيل FFmpeg لضمان معالجة الصوت دون كراش
static_ffmpeg.add_paths()
ua = UserAgent()

# هنا نسحب التوكن من منصة Railway فقط لمنع التضارب
TOKEN = os.getenv("BOT_TOKEN") 
ADMIN_ID = 8086158965 

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
    opts = {
        'outtmpl': 'file.%(ext)s',
        'quiet': True,
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

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("✅ البوت استقر الآن! أرسل رابط فيسبوك أو إنستغرام.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if url and "http" in url:
        link_id = save_link(url)
        keyboard = [[
            InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{link_id}"),
            InlineKeyboardButton("🎵 صوت MP3", callback_data=f"a|{link_id}")
        ]]
        await update.message.reply_text("📥 اختر النوع المطلوب:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    mode, link_id = query.data.split("|")
    url = get_link(link_id)
    status_msg = await query.edit_message_text("⏳ معالجة الطلب... يرجى الانتظار.")

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(mode)) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            if mode == 'a': filename = filename.rsplit('.', 1)[0] + ".mp3"

        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                if mode == 'v': await context.bot.send_video(chat_id=update.effective_chat.id, video=f)
                else: await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f)
            os.remove(filename)
            await status_msg.delete()
        else:
            await query.message.reply_text("❌ حدث خطأ في استخراج الملف.")
    except:
        await query.message.reply_text("⚠️ الرابط قد يكون خاصاً أو يحتاج كوكيز.")

if __name__ == '__main__':
    if not TOKEN:
        print("❌ خطأ: التوكن غير موجود في إعدادات Railway!")
    else:
        application = Application.builder().token(TOKEN).build()
        application.add_handler(CommandHandler("start", start))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        application.add_handler(CallbackQueryHandler(button_handler))
        
        # أهم سطر لإنهاء التضارب (Conflict) نهائياً
        application.run_polling(drop_pending_updates=True)
