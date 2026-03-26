import os
import asyncio
import yt_dlp
import static_ffmpeg
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# تفعيل FFmpeg بشكل ثابت
static_ffmpeg.add_paths()

TOKEN = os.getenv("BOT_TOKEN")

# إعدادات احترافية لتجاوز حظر المنصات
def get_ydl_opts(mode):
    opts = {
        'format': 'bestvideo+bestaudio/best' if mode == 'v' else 'bestaudio/best',
        'outtmpl': 'file.%(ext)s',
        'prefer_ffmpeg': True,
        'quiet': True,
        'no_warnings': True,
        # تمويه المتصفح لتجنب حظر إنستا وفيس بوك
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
        'add_header': [
            'Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language: en-us,en;q=0.5',
        ],
        'nocheckcertificate': True,
        'geo_bypass': True,
    }
    
    if mode == 'a':
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    return opts

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً بك في البوت المتكامل!\nأرسل رابطاً من (TikTok, Instagram, Facebook, YouTube).")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        keyboard = [
            [InlineKeyboardButton("🎬 فيديو (Video)", callback_data=f"v|{url}")],
            [InlineKeyboardButton("🎵 صوت (MP3)", callback_data=f"a|{url}")]
        ]
        await update.message.reply_text("📥 اختر الصيغة المطلوبة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode, url = query.data.split("|")
    
    status_msg = await query.edit_message_text("⏳ جاري المعالجة والتحميل... قد يستغرق الأمر لحظات.")

    try:
        # استخدام asyncio لتشغيل yt-dlp دون تجميد البوت
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(get_ydl_opts(mode)) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            if mode == 'a':
                filename = filename.rsplit('.', 1)[0] + ".mp3"

        with open(filename, 'rb') as f:
            if mode == 'v':
                await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption="✅ تم التحميل بواسطة بوتك.")
            else:
                await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f, caption="✅ تم تحويل الصوت بنجاح.")
        
        if os.path.exists(filename):
            os.remove(filename)
        await status_msg.delete()

    except Exception as e:
        error_text = str(e)
        if "login" in error_text.lower():
            await query.message.reply_text("❌ هذا الرابط يتطلب تسجيل دخول (حساب خاص). جرب روابط عامة.")
        else:
            await query.message.reply_text(f"⚠️ عذراً، حدث خطأ أثناء المعالجة.\nتأكد أن الرابط متاح للعامة.")
        print(f"Error detail: {error_text}")

if __name__ == '__main__':
    # استخدام drop_pending_updates لقتل أي تعارض قديم فوراً
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    print("🚀 البوت المتكامل يعمل الآن...")
    application.run_polling(drop_pending_updates=True)
