import os, glob, yt_dlp, asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

TOKEN = "8336468616:AAGcoSiyD1coEDRkDt1RPS77g_TwaMzd8bU"
# تم تثبيت المجلد ليكون متوافقاً مع سيرفرات Render
DOWNLOAD_DIR = "/tmp/downloads"

def download_media(url, mode='video'):
    if not os.path.exists(DOWNLOAD_DIR): os.makedirs(DOWNLOAD_DIR)
    for f in glob.glob(f"{DOWNLOAD_DIR}/*"): os.remove(f)
    
    ydl_opts = {
        'quiet': True, 'no_warnings': True, 'nocheckcertificate': True,
        'outtmpl': f'{DOWNLOAD_DIR}/allawi_file.%(ext)s',
        'http_headers': {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/122.0.0.0 Safari/537.36'}
    }
    if mode == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{'key': 'FFmpegExtractAudio','preferredcodec': 'mp3','preferredquality': '192'}]
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    files = glob.glob(f"{DOWNLOAD_DIR}/allawi_file.*")
    return files[0] if files else None

async def handle_msg(update, context):
    text = update.message.text
    if "http" in text:
        kb = [[InlineKeyboardButton("🎬 فيديو", callback_data=f"v|{text}"), InlineKeyboardButton("🎵 صوت", callback_data=f"a|{text}")]]
        await update.message.reply_text("اختر الصيغة المطلوبة:", reply_markup=InlineKeyboardMarkup(kb))

async def callback(update, context):
    q = update.callback_query
    mode, url = q.data.split('|')
    await q.answer()
    m = await q.edit_message_text("⏳ جاري التحميل... انتظر")
    try:
        path = await asyncio.to_thread(download_media, url, 'video' if mode == 'v' else 'audio')
        with open(path, 'rb') as f:
            if mode == 'v': await context.bot.send_video(q.message.chat_id, f)
            else: await context.bot.send_audio(q.message.chat_id, f)
        os.remove(path)
        await m.delete()
    except Exception as e:
        await q.message.reply_text(f"❌ حدث خطأ: {str(e)}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("أرسل الرابط الآن!")))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.run_polling()
