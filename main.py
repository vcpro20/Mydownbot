import os
import yt_dlp
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# جلب التوكن من إعدادات السيرفر (لأمان أكثر)
TOKEN = os.getenv("8336468616:AAGcoSiyD1coEDRkDt1RPS77g_TwaMzd8bU")

# إعدادات التحميل باستخدام yt-dlp
def download_media(url, mode='video'):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best' if mode == 'video' else 'bestaudio/best',
        'outtmpl': 'downloads/%(title)s.%(ext)s',
        'quiet': True,
        'no_warnings': True,
    }
    
    if mode == 'audio':
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(url, download=True)
        filename = ydl.prepare_filename(info)
        if mode == 'audio':
            filename = os.path.splitext(filename)[0] + ".mp3"
        return filename

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 أهلاً بك في بوت التحميل الذكي!\n\n"
        "أرسل لي رابطاً من (يوتيوب، فيسبوك، تيك توك، إنستغرام) وسأقوم بتحميله لك."
    )

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if not url.startswith("http"):
        await update.message.reply_text("❌ عذراً، هذا ليس رابطاً صحيحاً.")
        return

    keyboard = [
        [
            InlineKeyboardButton("🎬 فيديو (MP4)", callback_data=f"vid|{url}"),
            InlineKeyboardButton("🎵 صوت (MP3)", callback_data=f"aud|{url}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("اختر الصيغة التي تريد تحميلها:", reply_markup=reply_markup)

async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data, url = query.data.split("|")
    mode = 'video' if data == 'vid' else 'audio'
    
    status_msg = await query.edit_message_text("⏳ جاري المعالجة والتحميل... يرجى الانتظار")
    
    try:
        file_path = download_media(url, mode)
        
        with open(file_path, 'rb') as file:
            if mode == 'video':
                await query.message.reply_video(video=file, caption="✅ تم تحميل الفيديو بنجاح!")
            else:
                await query.message.reply_audio(audio=file, caption="✅ تم تحويل الصوت بنجاح!")
        
        # تنظيف المجلد وحذف الملف بعد الإرسال
        if os.path.exists(file_path):
            os.remove(file_path)
        await status_msg.delete()
        
    except Exception as e:
        await query.message.reply_text(f"❌ حدث خطأ أثناء المحاولة: {str(e)}")

def main():
    # التأكد من وجود مجلد التحميلات
    if not os.path.exists('downloads'):
        os.makedirs('downloads')

    if not TOKEN:
        print("Error: BOT_TOKEN variable is not set!")
        return

    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_click))

    print("🚀 البوت يعمل الآن...")
    app.run_polling()

if __name__ == "__main__":
    main()
