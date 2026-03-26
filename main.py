import os
import asyncio
import yt_dlp
import static_ffmpeg
from fake_useragent import UserAgent
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# تفعيل FFmpeg بشكل إلزامي لحل مشكلة "الصوت فقط"
static_ffmpeg.add_paths()
ua = UserAgent()

TOKEN = os.getenv("BOT_TOKEN")

def get_ydl_opts(mode):
    random_user_agent = ua.random
    
    opts = {
        # التحسين: إجبار البوت على اختيار أفضل جودة فيديو مدمجة
        'format': 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best' if mode == 'v' else 'bestaudio/best',
        'outtmpl': 'file.%(ext)s',
        'prefer_ffmpeg': True,
        'quiet': True,
        'no_warnings': True,
        'user_agent': random_user_agent,
        'nocheckcertificate': True,
        'ignoreerrors': True,
        # إضافة وسيطات خاصة بإنستغرام لتجاوز تقييد الفيديو
        'extractor_args': {
            'instagram': {
                'check_headers': True,
                'prefer_video': True # إجبار المستخرج على تفضيل الفيديو
            }
        },
        'http_headers': {
            'Accept': '*/*',
            'Accept-Language': 'en-US,en;q=0.5',
            'Referer': 'https://www.instagram.com/',
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
    await update.message.reply_text("أهلاً بك! 🫡\nالبوت الآن يدعم إنستغرام بجودة عالية.\nأرسل الرابط وسأقوم بالباقي.")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text
    if "http" in url:
        # إزالة زوائد الرابط التي تسبب مشاكل في إنستغرام
        clean_url = url.split('?')[0] if 'instagram.com' in url else url
        
        keyboard = [
            [InlineKeyboardButton("🎬 تحميل فيديو HD", callback_data=f"v|{clean_url}")],
            [InlineKeyboardButton("🎵 تحميل صوت فقط", callback_data=f"a|{clean_url}")]
        ]
        await update.message.reply_text("⚙️ جاري الفحص.. اختر الصيغة:", reply_markup=InlineKeyboardMarkup(keyboard))

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    mode, url = query.data.split("|")
    
    status_msg = await query.edit_message_text("⏳ معالجة الفيديو من إنستغرام... انتظر قليلاً.")

    try:
        loop = asyncio.get_event_loop()
        with yt_dlp.YoutubeDL(get_ydl_opts(mode)) as ydl:
            info = await loop.run_in_executor(None, lambda: ydl.extract_info(url, download=True))
            filename = ydl.prepare_filename(info)
            
            # معالجة لاحقة لضمان الامتداد الصحيح
            if mode == 'a':
                filename = filename.rsplit('.', 1)[0] + ".mp3"
            elif not filename.endswith(('.mp4', '.mkv', '.webm')):
                filename = filename.rsplit('.', 1)[0] + ".mp4"

        if os.path.exists(filename):
            with open(filename, 'rb') as f:
                if mode == 'v':
                    await context.bot.send_video(chat_id=update.effective_chat.id, video=f, caption="✅ تم تحميل فيديو إنستغرام.")
                else:
                    await context.bot.send_audio(chat_id=update.effective_chat.id, audio=f, caption="✅ تم تحويل الصوت.")
            
            os.remove(filename)
            await status_msg.delete()
        else:
            await query.message.reply_text("❌ فشل تكوين ملف الفيديو.")

    except Exception as e:
        await query.message.reply_text("⚠️ عذراً، إنستغرام يطلب تسجيل دخول لهذا الرابط.\nجرب روابط أخرى عامة (Public).")

if __name__ == '__main__':
    application = Application.builder().token(TOKEN).build()
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.run_polling(drop_pending_updates=True)
    
