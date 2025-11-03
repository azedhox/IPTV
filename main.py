import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import time
from PIL import Image
import pytesseract
import io

# إعداد السجلات
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# حالات المحادثة
WAITING_USERNAME = 1

# بيانات تسجيل الدخول
LOGIN_URL = "http://sl-cms.ddns.me/Account/Login"
ADD_M3U_URL = "http://sl-cms.ddns.me/Users/AddM3U"
SITE_USERNAME = "sh"
SITE_PASSWORD = "iptv1234"

# قائمة الباقات المطلوبة (Bouquet IDs)
SELECTED_BOUQUETS = [20, 35, 26, 25, 27, 113540, 113561, 113811]

class M3UBot:
    def __init__(self):
        self.driver = None
    
    def init_driver(self):
        """تهيئة متصفح Chrome"""
        chrome_options = Options()
        chrome_options.add_argument('--headless')  # وضع الخلفية
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        
        self.driver = webdriver.Chrome(options=chrome_options)
        return self.driver
    
    def solve_captcha(self):
        """حل الكابتشا الرياضية"""
        try:
            # البحث عن عنصر الكابتشا
            captcha_element = self.driver.find_element(By.ID, "captchaText")
            captcha_text = captcha_element.text.strip()
            
            # استخراج المعادلة (مثال: "5 + 3 = ?")
            match = re.search(r'(\d+)\s*\+\s*(\d+)', captcha_text)
            if match:
                num1 = int(match.group(1))
                num2 = int(match.group(2))
                result = num1 + num2
                return result
            
            # في حالة عدم وجود نمط معروف، محاولة OCR
            captcha_img = self.driver.find_element(By.ID, "captchaImage")
            screenshot = captcha_img.screenshot_as_png
            img = Image.open(io.BytesIO(screenshot))
            text = pytesseract.image_to_string(img)
            
            # محاولة استخراج الأرقام من النص
            numbers = re.findall(r'\d+', text)
            if len(numbers) >= 2:
                return int(numbers[0]) + int(numbers[1])
            
            return None
        except Exception as e:
            logger.error(f"خطأ في حل الكابتشا: {e}")
            return None
    
    def login(self):
        """تسجيل الدخول إلى الموقع"""
        try:
            self.driver.get(LOGIN_URL)
            time.sleep(2)
            
            # إدخال اسم المستخدم وكلمة المرور
            username_field = self.driver.find_element(By.ID, "Username")
            password_field = self.driver.find_element(By.ID, "Password")
            
            username_field.clear()
            username_field.send_keys(SITE_USERNAME)
            
            password_field.clear()
            password_field.send_keys(SITE_PASSWORD)
            
            # حل الكابتشا
            captcha_result = self.solve_captcha()
            if captcha_result:
                captcha_input = self.driver.find_element(By.ID, "CaptchaAnswer")
                captcha_input.clear()
                captcha_input.send_keys(str(captcha_result))
            else:
                logger.error("فشل في حل الكابتشا")
                return False
            
            # النقر على زر تسجيل الدخول
            login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            login_button.click()
            
            time.sleep(3)
            
            # التحقق من نجاح تسجيل الدخول
            if "Dashboard" in self.driver.title or "Home" in self.driver.title:
                logger.info("تم تسجيل الدخول بنجاح")
                return True
            else:
                logger.error("فشل تسجيل الدخول")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل الدخول: {e}")
            return False
    
    def create_trial(self, username):
        """إنشاء حساب تجريبي"""
        try:
            self.driver.get(ADD_M3U_URL)
            time.sleep(2)
            
            # إدخال اسم المستخدم
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "Username"))
            )
            username_field.clear()
            username_field.send_keys(username)
            
            # اختيار Package (1day/trial/mr)
            package_select = Select(self.driver.find_element(By.ID, "PackageId"))
            package_select.select_by_value("528")  # قيمة 1day/trial/mr
            
            time.sleep(2)
            
            # نقل الباقات المحددة من AllBouquets إلى SelectedBouquets
            for bouquet_id in SELECTED_BOUQUETS:
                try:
                    # تحديد الخيار في القائمة اليسرى
                    all_bouquets = self.driver.find_element(By.ID, "AllBouquets")
                    option = all_bouquets.find_element(By.CSS_SELECTOR, f"option[value='{bouquet_id}']")
                    
                    # تنفيذ JavaScript لتحديد ونقل الخيار
                    self.driver.execute_script("""
                        var option = arguments[0];
                        option.selected = true;
                        right();
                    """, option)
                    
                    time.sleep(0.5)
                except Exception as e:
                    logger.warning(f"تعذر إضافة الباقة {bouquet_id}: {e}")
            
            # تحديد جميع الخيارات في SelectedBouquets قبل الإرسال
            self.driver.execute_script("""
                $('#SelectedBouquets option').prop('selected', true);
            """)
            
            time.sleep(1)
            
            # النقر على زر Add
            add_button = self.driver.find_element(By.ID, "btnSend")
            add_button.click()
            
            time.sleep(3)
            
            # استخراج البيانات (URL أو معلومات الحساب)
            # يمكن تخصيص هذا الجزء بناءً على رد الموقع
            success_msg = "تم إنشاء الحساب بنجاح"
            
            # البحث عن رابط M3U أو بيانات الحساب
            account_info = {
                "username": username,
                "status": "تم الإنشاء بنجاح",
                "package": "1day/trial/mr",
                "duration": "24 ساعة"
            }
            
            return account_info
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء الحساب: {e}")
            return None
    
    def close_driver(self):
        """إغلاق المتصفح"""
        if self.driver:
            self.driver.quit()

# إنشاء instance من البوت
bot_instance = M3UBot()

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /start"""
    welcome_message = """
🎬 مرحباً بك في بوت إنشاء Trial M3U

للحصول على حساب تجريبي لمدة 24 ساعة، يرجى إرسال اسم المستخدم الذي تريده.

📝 أرسل اسم المستخدم الآن:
    """
    await update.message.reply_text(welcome_message)
    return WAITING_USERNAME

async def create_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج إنشاء الحساب"""
    username = update.message.text.strip()
    
    if not username or len(username) > 20:
        await update.message.reply_text("❌ اسم المستخدم غير صالح. يجب أن يكون أقل من 20 حرف.")
        return WAITING_USERNAME
    
    await update.message.reply_text("⏳ جارٍ إنشاء الحساب التجريبي... يرجى الانتظار")
    
    try:
        # تهيئة المتصفح
        bot_instance.init_driver()
        
        # تسجيل الدخول
        if not bot_instance.login():
            await update.message.reply_text("❌ فشل تسجيل الدخول إلى الموقع")
            bot_instance.close_driver()
            return ConversationHandler.END
        
        # إنشاء الحساب
        account_info = bot_instance.create_trial(username)
        
        if account_info:
            response = f"""
✅ تم إنشاء الحساب التجريبي بنجاح!

👤 اسم المستخدم: {account_info['username']}
📦 الباقة: {account_info['package']}
⏱ المدة: {account_info['duration']}

📺 الباقات المفعلة:
• FRANCE VIP 🇫🇷
• SPAIN 🇪🇸
• ITALIA 🇮🇹
• GERMANY VIP 🇩🇪
• SKY ITALIA VIP 🇮🇹
• BEIN SPORTS ARABIA VIP+ 🏆
• ARABIC SPORTS CINEMA VIP 🎬
• DSTV 📡

استمتع بالمشاهدة! 🍿
            """
            await update.message.reply_text(response)
        else:
            await update.message.reply_text("❌ فشل إنشاء الحساب. يرجى المحاولة لاحقاً")
        
        # إغلاق المتصفح
        bot_instance.close_driver()
        
    except Exception as e:
        logger.error(f"خطأ عام: {e}")
        await update.message.reply_text("❌ حدث خطأ أثناء إنشاء الحساب")
        bot_instance.close_driver()
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية"""
    await update.message.reply_text("تم إلغاء العملية. أرسل /start للبدء من جديد")
    return ConversationHandler.END

def main():
    """تشغيل البوت"""
    # ضع هنا رمز البوت الخاص بك من @BotFather
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    # إنشاء التطبيق
    application = Application.builder().token(TOKEN).build()
    
    # إضافة معالج المحادثة
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            WAITING_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    
    # بدء البوت
    logger.info("البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
