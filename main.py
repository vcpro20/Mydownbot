import os
import asyncio
import yt_dlp
import static_ffmpeg
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# تفعيل المسارات لضمان دمج وفصل الوسائط
static_ffmpeg.add_paths()
ua = UserAgent()

TOKEN = os.getenv("BOT_TOKEN")

def get_ydl_opts(mode, url):
    random_user_agent = ua.random
    
    # إعدادات عامة مرنة لضمان قراءة فيسبوك وغيره
    opts = {
        'outtmpl': 'file.%(ext)s',
        'prefer_ffmpeg': True,
        'quiet': True,
        'no_warnings': True,
        'user_agent': random_user_agent,
        'nocheckcertificate': True,
        'ignoreerrors': True,
    }

    # حل مشكلة إنستغرام (فيديو أو صوت) مع الحفاظ على فيسبوك
    if mode == 'v':
        # نطلب أفضل فيديو وأفضل صوت متاحين مهما كان نوعهما
        opts['format'] = 'bestvideo+bestaudio/best'
    else:
        # نطلب أفضل صوت فقط
        opts['format'] = 'bestaudio/best'
        opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]

    # تخصيص لإنستغرام وفيسبوك لزيادة التوافق
    opts['extractor_args'] = {
        'instagram': {'check_headers': True},
        'facebook': {'force_get_url': True}
    }
    
    return opts

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إصلاح كافة المشاكل! 🛠️\nالآن يدعم: (فيديو/صوت) لإنستغرام + روابط فيسبوك بنجاح.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        # تنظيف الرابط بشكل لا يفسد معالجة فيسبوك
        clean_url = url.split('?')[0] if 'instagram.com' in url else url
        
        keyboard = [
            [InlineKeyboardButton("🎬 تحميل فيديو", callback_data=f"v|{clean_url}")],
            [InlineKeyboardButton("🎵 تحميل صوت MP3", callback_data=f"a|{clean_url}")]
        ]
        await update.message.reply_text("📥 اختر ما تريد تحميله:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode, url = query.data.split("|")
    
    status_msg = await query.edit_message_text("⏳ جاري التحميل... يرجى الانتظار.")

    try:
        # إرسال الرابط والوضع للدالة المحدثة
        with yt_dlp.YoutubeDL(get_ydl_opts(mode, url)) as ydl:
            info = await asyncio.get_event_loop().run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            
            if mode == 'a':
                filename = filename.rsplit('.', 1)[0] + ".mp3"

        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                if mode == 'v':
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption="✅ فيديو جاهز.")
                else:
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f, caption="✅ ملف صوتي جاهز.")
            
            os.remove(filename)
            await status_msg.delete()
        else:
            await query.message.reply_text("❌ لم أتمكن من إيجاد الملف بعد تحميله.")

    except Exception as e:
        print(f"Error: {e}")
        await query.message.reply_text("⚠️ خطأ في المنصة أو الرابط محمي. تأكد أن الحساب عام (Public).")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling(drop_pending_updates=True)
    
