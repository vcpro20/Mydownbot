import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# --- إضافة هذه الأسطر الجديدة هنا ---
import static_ffmpeg
static_ffmpeg.add_paths() 
# ----------------------------------

TOKEN = os.getenv("BOT_TOKEN")

# باقي الكود كما هو...

# إعدادات yt-dlp مع تحديد مسار التحميل
def get_ydl_opts(mode):
    opts = {
        'format': 'best' if mode == 'v' else 'bestaudio/best',
        'outtmpl': 'file.%(ext)s',
        'prefer_ffmpeg': True,
    }
    if mode == 'a':
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    return opts

async def start(update, context):
    await update.message.reply_text("👋 أهلاً علاوي! أرسل رابط الفيديو للتحميل.")

async def handle_msg(update, context):
    url = update.message.text
    if "http" in url:
        btns = [[InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{url}"), 
                 InlineKeyboardButton("🎵 صوت", callback_data=f"a|{url}")]]
        await update.message.reply_text("اختر الصيغة:", reply_markup=InlineKeyboardMarkup(btns))

async def run_down(update, context):
    query = update.callback_query
    await query.answer()
    mode, url = query.data.split("|")
    msg = await query.edit_message_text("⏳ جاري المعالجة...")

    try:
        with yt_dlp.YoutubeDL(get_ydl_opts(mode)) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            if mode == 'a': path = path.rsplit('.', 1)[0] + ".mp3"
        
        with open(path, 'rb') as f:
            if mode == 'v': await context.bot.send_video(chat_id=query.message.chat_id, video=f)
            else: await context.bot.send_audio(chat_id=query.message.chat_id, audio=f)
        
        if os.path.exists(path): os.remove(path)
        await msg.delete()
    except Exception as e:
        await query.message.reply_text(f"❌ خطأ: {str(e)}\nتأكد من تحديث FFmpeg في السيرفر.")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(run_down))
    app.run_polling(drop_pending_updates=True) # هذا السطر سيحل مشكلة الـ Conflict
