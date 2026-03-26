import os, asyncio, sqlite3, yt_dlp, static_ffmpeg, uuid
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

static_ffmpeg.add_paths()
ua = UserAgent()

TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = 8086158965

# قاعدة بيانات لحفظ المستخدمين والروابط الطويلة
def init_db():
    conn = sqlite3.connect('bot_data.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    # جدول لتخزين الروابط الطويلة (حل مشكلة Button_data_invalid)
    c.execute('''CREATE TABLE IF NOT EXISTS links (id TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

def save_link(url):
    link_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect('bot_data.db')
    conn.execute("INSERT INTO links (id, url) VALUES (?, ?)", (link_id, url))
    conn.commit()
    conn.close()
    return link_id

def get_link(link_id):
    conn = sqlite3.connect('bot_data.db')
    row = conn.execute("SELECT url FROM links WHERE id=?", (link_id,)).fetchone()
    conn.close()
    return row[0] if row else None

init_db()

def get_ydl_opts(mode):
    return {
        'format': 'bestvideo+bestaudio/best' if mode == 'v' else 'bestaudio/best',
        'outtmpl': 'file.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True,
        'extractor_args': {'facebook': {'force_get_url': True}},
        'http_headers': {'User-Agent': ua.random, 'Referer': 'https://www.facebook.com/'}
    }

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 تم إصلاح روابط فيسبوك بنجاح!\nأرسل الرابط الآن.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        # حل مشكلة Button_data_invalid عبر حفظ الرابط برقم تعريفي قصير
        link_id = save_link(url)
        keyboard = [[
            InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{link_id}"),
            InlineKeyboardButton("🎵 صوت", callback_data=f"a|{link_id}")
        ]]
        await update.message.reply_text("📥 اختر الصيغة المطلوب تحميلها من فيسبوك:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data_parts = query.data.split("|")
    mode = data_parts[0]
    link_id = data_parts[1]
    
    # استرجاع الرابط الحقيقي من قاعدة البيانات
    url = get_link(link_id)
    if not url:
        await query.edit_message_text("⚠️ الرابط منتهي الصلاحية، أرسله مجدداً.")
        return

    status_msg = await query.edit_message_text("⏳ جاري سحب الفيديو من فيسبوك...")

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
        await query.message.reply_text("❌ فيسبوك يرفض الاتصال، تأكد أن الفيديو عام (Public).")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling(drop_pending_updates=True)
