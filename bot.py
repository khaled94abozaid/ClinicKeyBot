import os
import hashlib
import hmac
import base64
import qrcode
from io import BytesIO
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, PreCheckoutQueryHandler, filters
from telegram.constants import ParseMode

# ========== التوكن من متغيرات البيئة (آمن) ==========
TOKEN = os.environ.get("BOT_TOKEN")

# ========== المفتاح السري (نفس الموجود في تطبيقك) ==========
SECRET_KEY = b'Kh@l3d$MyCl1n!c#2024*S3cur3'

def generate_activation_key(lock_code: str) -> str:
    """توليد مفتاح التفعيل بنفس خوارزمية التطبيق"""
    try:
        h = hmac.new(SECRET_KEY, lock_code.encode('utf-8'), hashlib.sha256)
        b64 = base64.b64encode(h.digest()).decode('utf-8')
        clean = ''.join([c for c in b64 if c.isalnum()])[:16]
        return clean if clean else "INVALID"
    except Exception:
        return "INVALID"

def generate_qr(text: str) -> BytesIO:
    """توليد QR Code"""
    qr = qrcode.QRCode(version=5, error_correction=qrcode.constants.ERROR_CORRECT_H, box_size=8, border=2)
    qr.add_data(text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    bio = BytesIO()
    bio.name = "key_qr.png"
    img.save(bio, "PNG")
    bio.seek(0)
    return bio

# ========== أوامر البوت ==========
async def start(update: Update, context):
    await update.message.reply_text(
        "🤖 *بوت تفعيل ClinicKey*\n\n💰 للشراء: /buy\n📌 بعد الدفع، أرسل كود القفل",
        parse_mode=ParseMode.MARKDOWN
    )

async def buy(update: Update, context):
    await context.bot.send_invoice(
        chat_id=update.effective_chat.id,
        title="🔑 تفعيل ClinicKey",
        description="مفتاح تفعيل لبرنامج العيادات",
        payload="key_" + str(update.effective_user.id),
        provider_token="",
        currency="XTR",
        prices=[{"label": "مفتاح التفعيل", "amount": 1000}]
    )

async def pre_checkout(update: Update, context):
    await update.pre_checkout_query.answer(ok=True)

async def successful_payment(update: Update, context):
    context.user_data['paid'] = True
    await update.message.reply_text("✅ تم الدفع! أرسل كود القفل (Lock Code) الآن.")

async def handle_lock_code(update: Update, context):
    if not context.user_data.get('paid'):
        await update.message.reply_text("⚠️ أرسل /buy أولاً")
        return
    
    lock_code = update.message.text.strip()
    if len(lock_code) < 3:
        await update.message.reply_text("❌ كود القفل قصير جداً")
        return
    
    activation_key = generate_activation_key(lock_code)
    if activation_key == "INVALID":
        await update.message.reply_text("❌ خطأ في التوليد")
        return
    
    qr_image = generate_qr(activation_key)
    await update.message.reply_photo(
        photo=qr_image,
        caption=f"✅ مفتاح التفعيل: `{activation_key}`",
        parse_mode=ParseMode.MARKDOWN
    )
    context.user_data['paid'] = False

# ========== تشغيل البوت ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("buy", buy))
    app.add_handler(PreCheckoutQueryHandler(pre_checkout))
    app.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_lock_code))
    print("✅ البوت شغال...")
    app.run_polling()

if __name__ == "__main__":
    main()