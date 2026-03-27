import os, asyncio, sqlite3, yt_dlp, static_ffmpeg, uuid
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

static_ffmpeg.add_paths()
ua = UserAgent()

TOKEN = os.getenv("BOT_TOKEN") or "ضـع_تـوكـن_بـوتـك_هـنـا" 
ADMIN_ID =  8086158965

# --- [1] إدارة قاعدة البيانات (لمنع أخطاء البيانات الطويلة) ---
def init_db():
    conn = sqlite3.connect('pro_v_modular.db')
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY)''')
    c.execute('''CREATE TABLE IF NOT EXISTS links (id TEXT PRIMARY KEY, url TEXT)''')
    conn.commit()
    conn.close()

def save_link(url):
    link_id = str(uuid.uuid4())[:8]
    conn = sqlite3.connect('pro_v_modular.db')
    conn.execute("INSERT INTO links (id, url) VALUES (?, ?)", (link_id, url))
    conn.commit()
    conn.close()
    return link_id

def get_link(link_id):
    conn = sqlite3.connect('pro_v_modular.db')
    row = conn.cursor().execute("SELECT url FROM links WHERE id=?", (link_id,)).fetchone()
    conn.close()
    return row[0] if row else None

init_db()

# --- [2] دالة منفردة لتحميل يوتيوب (تمنع التضارب) ---
async def download_youtube(url, mode):
    opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if mode == 'v' else 'bestaudio/best',
        'user_agent': ua.random,
    }
    if mode == 'a':
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename)[0] + ".mp3" if mode == 'a' else filename

# --- [3] دالة منفردة للمنصات الأخرى (فيس، إنستا، تيك توك) ---
async def download_social(url, mode):
    opts = {
        'outtmpl': 'downloads/%(id)s.%(ext)s',
        'quiet': True,
        'nocheckcertificate': True,
        'user_agent': ua.random,
        'format': 'bestvideo+bestaudio/best' if mode == 'v' else 'bestaudio/best',
        'extractor_args': {
            'facebook': {'force_get_url': True},
            'instagram': {'check_headers': True},
            'tiktok': {'web_proxy': True}
        },
        'http_headers': {'Referer': 'https://www.google.com/'}
    }
    if mode == 'a':
        opts['postprocessors'] = [{'key': 'FFmpegExtractAudio', 'preferredcodec': 'mp3', 'preferredquality': '192'}]
    
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
        filename = ydl.prepare_filename(info)
        return os.path.splitext(filename)[0] + ".mp3" if mode == 'a' else filename

# --- [4] المعالج الرئيسي وتوزيع المهام ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "broadcast":
        context.user_data['waiting_broadcast'] = True
        await query.message.reply_text("📥 أرسل محتوى الإذاعة.")
        return

    mode, link_id = query.data.split("|")
    url = get_link(link_id)
    if not os.path.exists('downloads'): os.makedirs('downloads')
    
    status_msg = await query.edit_message_text("⏳ جاري المعالجة بنظام الدوال المنفصلة...")

    try:
        # هنا يتم توجيه الرابط للدالة المناسبة لمنع التضارب
        if any(x in url for x in ['youtube.com', 'youtu.be']):
            file
            
