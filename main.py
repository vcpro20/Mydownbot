import os
import asyncio
import yt_dlp
import static_ffmpeg
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# 1. تفعيل FFmpeg تلقائياً لحل مشكلة "ffprobe not found" التي ظهرت في سجلاتك
static_ffmpeg.add_paths()
ua = UserAgent()

# جلب التوكن من متغيرات البيئة في Railway
TOKEN = os.getenv("BOT_TOKEN")

def get_ydl_opts(mode):
    # استخدام هوية متصفح عشوائية لتقليل احتمالية الحظر بدون كوكيز
    random_user_agent = ua.random
    
    opts = {
        'format': 'bestvideo+bestaudio/best' if mode == 'v' else 'bestaudio/best',
        'outtmpl': 'file.%(ext)s',
        'prefer_ffmpeg': True,
        'quiet': True,
        'no_warnings': True,
        'user_agent': random_user_agent,
        'referer': 'https://www.facebook.com/',
        'nocheckcertificate': True,
        'geo_bypass': True,
        'extract_flat': False,
        'cachedir': False,
        'ignoreerrors': True,
        # تحسينات إضافية لتجاوز جدران الحماية برمجياً
        'extractor_args': {
            'youtube': {'player_client': ['android', 'web']},
            'instagram': {'check_headers': True},
            'facebook': {'force_get_url': True}
        },
        'http_headers': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-us,en;q=0.5',
            'Connection': 'keep-alive',
        }
    }
    
    if mode == 'a':
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    return opts

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("👋 أهلاً عزيزي/تي! البوت المطور جاهز للعمل.\nأرسل رابط فيديو من (TikTok, Instagram, Facebook) للبدء.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        # تنظيف الروابط لضمان أعلى توافقية
        clean_url = url.split('?')[0] if 'instagram.com' in url or 'facebook.com' in url else url
        
        keyboard = [
            [InlineKeyboardButton("🎬 تحميل فيديو", callback_data=f"v|{clean_url}")],
            [InlineKeyboardButton("🎵 تحويل لصوت MP3", callback_data=f"a|{clean_url}")]
        ]
        await update.message.reply_text("📥 اختر الإجراء المطلوب:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode, url = query.data.split("|")
    
    status_msg = await query.edit_message_text("⏳ جاري معالجة الرابط... قد يستغرق الأمر ثواني.")

    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(get_ydl_opts(mode)) as ydl:
            # تنفيذ عملية التحميل في خيط منفصل لمنع تجميد البوت
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            
            if not info:
                raise Exception("فشل استخراج البيانات.")

            filename = ydl.prepare_filename(info)
            if mode == 'a':
                filename = filename.rsplit('.', 1)[0] + ".mp3"

        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                if mode == 'v':
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption="✅ تم تحميل الفيديو.")
                else:
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f, caption="✅ تم تحميل الصوت.")
            
            # حذف الملف بعد الإرسال لتوفير مساحة السيرفر
            os.remove(filename)
            await status_msg.delete()
        else:
            await query.message.reply_text("❌ لم يتم العثور على الملف بعد المعالجة.")

    except Exception as e:
        print(f"Error: {str(e)}")
        await query.message.reply_text("⚠️ عذراً، هذا الرابط محمي أو غير متاح للتحميل حالياً بدون كوكيز.")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    
    # حل مشكلة Conflict عبر تجاهل التحديثات المعلقة عند التشغيل
    application.run_polling(drop_pending_updates=True)
    
