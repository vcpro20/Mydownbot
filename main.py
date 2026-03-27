import os, asyncio, sqlite3, yt_dlp, static_ffmpeg, uuid
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

static_ffmpeg.add_paths()
ua = UserAgent()

TOKEN = os.getenv("BOT_TOKEN") or "ضـع_تـوكـن_بـوتـك_هـنـا" 
ADMIN_ID = 8086158965 

# --- إدارة قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('pro_v_final_secure.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS links (id TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

def save_link(url):
    link_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect('pro_v_final_secure.db')
    conn.execute("INSERT INTO links (id, url) VALUES (?, ?)", (link_id, url))
    conn.commit()
    conn.close()
    return link_id

def get_link(link_id):
    conn = sqlite3.connect('pro_v_final_secure.db')
    row = conn.cursor().execute("SELECT url FROM links WHERE id=?", (link_id,)).fetchone()
    conn.close()
    return row[0] if row else None

init_db()

# --- [دالة يوتيوب مع ميزات تجاوز الحظر] ---
async def youtube_worker(url, mode):
    opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if mode == 'v' else 'bestaudio/best',
        # ميزات تجاوز الحظر الجديدة
        'nocheckcertificate': True,
        'geo_bypass': True,
        'http_headers': {
            'User-Agent': ua.random,
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
        }
    }
    # إذا قمت برفع ملف باسم cookies.txt بجانب الكود، قم بإلغاء التعليق عن السطر التالي
    # opts['cookiefile'] = 'cookies.txt' 

    if mode == 'a':
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename)[0] + ".mp3" if mode == 'a' else filename

# --- [دالة المنصات الاجتماعية] ---
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

# --- المعالج والتحكم ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    mode, link_id = query.data.split("|")
    url = get_link(link_id)
    if not os.path.exists('downloads'): os.makedirs('downloads')
    
    status_msg = await query.edit_message_text("⏳ جاري محاولة تجاوز القيود والتحميل...")

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
        # رسالة خطأ توضح السبب التقني
        await query.message.reply_text(f"⚠️ يوتيوب يطلب الكوكيز حالياً. جرب رابطاً آخر أو أرسل لي ملف cookies.txt\n\nالخطأ: {str(e)[:100]}...")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text and "http" in update.message.text:
        link_id = save_link(update.message.text)
        keyboard = [[InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{link_id}"), 
                     InlineKeyboardButton("🎵 صوت", callback_data=f"a|{link_id}")]]
        await update.message.reply_text("📥 تم استلام الرابط بنظام الدوال الآمنة:", reply_markup=InlineKeyboardMarkup(keyboard))

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    # حل مشكلة الـ Conflict وتكرار البوت
    application.run_polling(drop_pending_updates=True)
