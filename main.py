import os
import glob
import yt_dlp
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# إعداد السجلات لمراقبة أداء البوت
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# جلب التوكن من إعدادات Railway
TOKEN = os.getenv("BOT_TOKEN")

# المجلد المؤقت للتحميل
DOWNLOAD_DIR = "/tmp/downloads"

def download_media(url, mode='video'):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    # تنظيف المجلد قبل التحميل
    for f in glob.glob(f"{DOWNLOAD_DIR}/*"):
        try: os.remove(f)
        except: pass
    
    # إعدادات شاملة لجميع المنصات
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'outtmpl': f'{DOWNLOAD_DIR}/allawi_result.%(ext)s',
        'restrictfilenames': True,
        # وكيل مستخدم حديث لتجاوز حظر إنستغرام وفيسبوك
        'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'referer': 'https://www.google.com/',
    }

    if mode == 'video':
        # اختيار أفضل جودة فيديو مدمجة مع الصوت تلقائياً
        ydl_opts['format'] = 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/best[ext=mp4]/best'
    else:
        # إعدادات استخراج الصوت MP3 (تتطلب FFmpeg في السيرفر)
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    # البحث عن الملف الناتج
    files = glob.glob(f"{DOWNLOAD_DIR}/allawi_result.*")
    return files[0] if files else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🚀 أهلاً بك في بوت التحميل الشامل!\n\n"
        "دعم كامل لـ: ✅ يوتيوب ✅ تيك توك ✅ إنستغرام ✅ فيسبوك\n\n"
        "أرسل الرابط الآن للبدء..",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📊 حالة السيرفر")]], resize_keyboard=True)
    )

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "http" in text:
        # تنظيف الرابط من أي نصوص إضافية
        url = text.split()[0]
        keyboard = [
            [
                InlineKeyboardButton("🎬 فيديو (MP4)", callback_data=f"v|{url}"),
                InlineKeyboardButton("🎵 صوت (MP3)", callback_data=f"a|{url}")
            ]
        ]
        await update.message.reply_text("📥 اختر النوع المطلوب:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif text == "📊 حالة السيرفر":
        await update.message.reply_text("✅ السيرفر يعمل بكفاءة عالية على Railway.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mode, url = query.data.split('|')
    await query.answer()
    
    status_msg = await query.edit_message_text("⏳ جاري المعالجة.. قد يستغرق الأمر ثواني حسب حجم الملف.")
    
    try:
        # تشغيل التحميل في خيط منفصل لمنع تعليق البوت
        path = await asyncio.to_thread(download_media, url, mode)
        
        if path and os.path.exists(path):
            await query.edit_message_text("📤 جاري إرسال الملف إلى تلجرام...")
            with open(path, 'rb') as f:
                if mode == 'v':
                    await context.bot.send_video(chat_id=query.message.chat_id, video=f, caption="✅ تم التحميل بنجاح | @vcpro20")
                else:
                    await context.bot.send_audio(chat_id=query.message.chat_id, audio=f, caption="🎵 تم تحويل الصوت بنجاح | @vcpro20")
            
            # مسح الملف فوراً لتوفير مساحة
            os.remove(path)
            await status_msg.delete()
        else:
            await query.message.reply_text("❌ عذراً، لم أتمكن من جلب الملف. تأكد أن الرابط عام وليس خاص.")
    except Exception as e:
        logging.error(f"Error: {e}")
        await query.message.reply_text("⚠️ حدث خطأ تقني. يرجى التأكد من تثبيت FFmpeg في السيرفر لتحميل الصوت.")

if __name__ == '__main__':
    if not TOKEN:
        print("Error: BOT_TOKEN not found!")
    else:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
        
        print("البوت الشامل يعمل الآن...")
        app.run_polling()
        
