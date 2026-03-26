import os
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# الحصول على التوكن
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("🚀 أرسل رابط الفيديو الآن (TikTok, YT, Instagram)")

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        btns = [
            [InlineKeyboardButton("🎬 فيديو MP4", callback_data=f"v|{url}")],
            [InlineKeyboardButton("🎵 صوت MP3", callback_data=f"a|{url}")]
        ]
        await update.message.reply_text("📥 اختر الصيغة:", reply_markup=InlineKeyboardMarkup(btns))

async def process(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode, url = query.data.split("|")
    
    status = await query.edit_message_text("⏳ جاري التحميل...")

    ydl_opts = {
        'format': 'best' if mode == 'v' else 'bestaudio/best',
        'outtmpl': 'file.%(ext)s',
    }
    
    if mode == 'a':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            path = ydl.prepare_filename(info)
            if mode == 'a': path = path.rsplit('.', 1)[0] + ".mp3"

        with open(path, 'rb') as f:
            if mode == 'v':
                await context.bot.send_video(chat_id=query.message.chat_id, video=f)
            else:
                await context.bot.send_audio(chat_id=query.message.chat_id, audio=f)
        
        if os.path.exists(path): os.remove(path)
        await status.delete()
    except Exception as e:
        await query.message.reply_text(f"❌ خطأ: {str(e)}")

if __name__ == '__main__':
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
    app.add_handler(CallbackQueryHandler(process))
    print("Bot is running...")
    app.run_polling()
