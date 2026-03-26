import os
import asyncio
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# جلب التوكن من Variables
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً علاوي! أرسل رابط الفيديو للبدء.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        keyboard = [
            [InlineKeyboardButton("🎬 فيديو MP4", callback_data=f"v|{url}")],
            [InlineKeyboardButton("🎵 صوت MP3", callback_data=f"a|{url}")]
        ]
        await update.message.reply_text("اختر الصيغة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode, url = query.data.split("|")
    
    msg = await query.edit_message_text("⏳ جاري التحميل... انتظر قليلاً.")

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
            filename = ydl.prepare_filename(info)
            if mode == 'a': 
                filename = filename.rsplit('.', 1)[0] + ".mp3"

        with open(filename, 'rb') as f:
            if mode == 'v':
                await context.bot.send_video(chat_id=update.effective_chat.id, video=f)
            else:
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f)
        
        if os.path.exists(filename): 
            os.remove(filename)
        await msg.delete()

    except Exception as e:
        await query.message.reply_text(f"❌ خطأ: {str(e)}")

if __name__ == '__main__':
    # هذه هي الطريقة الصحيحة للإصدار v20+
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    print("Bot is starting...")
    application.run_polling()
    
