import os
import glob
import yt_dlp
import asyncio
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackQueryHandler, ContextTypes

# إعداد السجلات (Logs) لمراقبة أداء البوت على Railway
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# جلب التوكن من إعدادات المنصة (Variables) لحمايته
TOKEN = os.getenv("BOT_TOKEN")

# مسار التحميل المؤقت المتوافق مع السيرفرات السحابية
DOWNLOAD_DIR = "/tmp/downloads"

def download_media(url, mode='video'):
    if not os.path.exists(DOWNLOAD_DIR):
        os.makedirs(DOWNLOAD_DIR)
    
    # تنظيف المجلد قبل كل عملية تحميل جديدة لتوفير المساحة
    for f in glob.glob(f"{DOWNLOAD_DIR}/*"):
        try: os.remove(f)
        except: pass
    
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'nocheckcertificate': True,
        'outtmpl': f'{DOWNLOAD_DIR}/allawi_file.%(ext)s',
        'http_headers': {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36'
        }
    }

    if mode == 'audio':
        ydl_opts['format'] = 'bestaudio/best'
        ydl_opts['postprocessors'] = [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }]
    
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])
    
    files = glob.glob(f"{DOWNLOAD_DIR}/allawi_file.*")
    return files[0] if files else None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user.first_name
    await update.message.reply_text(
        f"أهلاً بك يا {user} في بوت التحميل الخاص بـ Allawi!\n\nأرسل رابط فيديو من (إنستغرام، فيسبوك، يوتيوب، تيك توك) وسأقوم بمعالجته فوراً.",
        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("📊 حالة السيرفر")]], resize_keyboard=True)
    )

async def handle_msg(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if "http" in text:
        keyboard = [
            [
                InlineKeyboardButton("🎬 فيديو (MP4)", callback_data=f"v|{text}"),
                InlineKeyboardButton("🎵 صوت (MP3)", callback_data=f"a|{text}")
            ]
        ]
        await update.message.reply_text("اختر الصيغة المطلوبة للتحميل:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif text == "📊 حالة السيرفر":
        await update.message.reply_text("✅ السيرفر يعمل بنجاح على منصة Railway.")

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    mode, url = query.data.split('|')
    await query.answer()
    
    status_msg = await query.edit_message_text("⏳ جاري التحميل والمعالجة... يرجى الانتظار")
    
    try:
        # تنفيذ التحميل في خيط منفصل لعدم تعليق البوت
        path = await asyncio.to_thread(download_media, url, 'video' if mode == 'v' else 'audio')
        
        if path and os.path.exists(path):
            with open(path, 'rb') as f:
                if mode == 'v':
                    await context.bot.send_video(chat_id=query.message.chat_id, video=f, caption="✅ تم التحميل بنجاح | @vcpro20")
                else:
                    await context.bot.send_audio(chat_id=query.message.chat_id, audio=f, caption="✅ تم تحويل الصوت بنجاح | @vcpro20")
            
            os.remove(path) # مسح الملف بعد الإرسال لتوفير مساحة السيرفر
            await status_msg.delete()
        else:
            await query.message.reply_text("❌ عذراً، لم أتمكن من تحميل الملف. قد يكون الرابط خاصاً أو غير مدعوم.")
    except Exception as e:
        logging.error(f"Error: {e}")
        await query.message.reply_text("❌ حدث خطأ تقني. تأكد من صحة الرابط أو حاول لاحقاً.")

if __name__ == '__main__':
    if not TOKEN:
        print("خطأ: لم يتم العثور على BOT_TOKEN في إعدادات البيئة!")
    else:
        app = Application.builder().token(TOKEN).build()
        app.add_handler(CommandHandler("start", start))
        app.add_handler(CallbackQueryHandler(button_callback))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_msg))
        
        print("البوت يعمل الآن على Railway...")
        app.run_polling()
        
