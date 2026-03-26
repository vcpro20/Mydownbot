import os
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes
import yt_dlp

# جلب التوكن من المتغيرات
TOKEN = os.getenv("BOT_TOKEN")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك! أرسل لي رابطاً من (يوتيوب، تيك توك، إنستغرام) للبدء.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        keyboard = [
            [InlineKeyboardButton("🎬 فيديو (Video)", callback_data=f"vid|{url}")],
            [InlineKeyboardButton("🎵 صوت (MP3)", callback_data=f"aud|{url}")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("اختر الصيغة المطلوبة:", reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data, url = query.data.split("|")
    
    msg = await query.edit_message_text("⏳ جاري المعالجة... قد يستغرق الأمر ثواني.")

    ydl_opts = {
        'format': 'best' if data == "vid" else 'bestaudio/best',
        'outtmpl': 'downloaded_file.%(ext)s',
        'noplaylist': True,
    }

    if data == "aud":
        ydl_opts.update({
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        })

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)
            if data == "aud":
                filename = filename.rsplit('.', 1)[0] + ".mp3"

        with open(filename, 'rb') as f:
            if data == "vid":
                await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption="✅ تم تحميل الفيديو بنجاح.")
            else:
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f, caption="✅ تم تحميل الصوت بنجاح.")
        
        os.remove(filename)
        await msg.delete()

    except Exception as e:
        await query.message.reply_text(f"⚠️ خطأ تقني: تأكد من أن الرابط مدعوم أو حاول لاحقاً.\nوصف الخطأ: {str(e)}")

def main():
    if not TOKEN:
        print("❌ Error: BOT_TOKEN not found!")
        return
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))
    print("🚀 البوت يعمل الآن...")
    app.run_polling()

if __name__ == '__main__':
    main()
    
