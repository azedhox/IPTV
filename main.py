import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait, Select
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
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
        try:
            chrome_options = Options()
            # إزالة headless للاختبار - يمكنك إضافته لاحقاً
            # chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--lang=ar')
            
            # استخدام webdriver_manager لتثبيت driver تلقائياً
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # إخفاء خاصية webdriver
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("تم تهيئة المتصفح بنجاح")
            return self.driver
        except Exception as e:
            logger.error(f"خطأ في تهيئة المتصفح: {e}")
            return None
    
    def solve_captcha(self):
        """حل الكابتشا الرياضية"""
        try:
            time.sleep(1)
            
            # البحث عن نص الكابتشا بطرق متعددة
            captcha_text = None
            
            # محاولة 1: البحث عن label أو span يحتوي على المعادلة
            try:
                captcha_labels = self.driver.find_elements(By.TAG_NAME, "label")
                for label in captcha_labels:
                    text = label.text.strip()
                    if '+' in text or '=' in text:
                        captcha_text = text
                        break
            except:
                pass
            
            # محاولة 2: البحث في كل النصوص الظاهرة
            if not captcha_text:
                try:
                    page_text = self.driver.find_element(By.TAG_NAME, "body").text
                    # البحث عن نمط المعادلة في الصفحة
                    match = re.search(r'(\d+)\s*\+\s*(\d+)\s*=\s*\?', page_text)
                    if match:
                        captcha_text = match.group(0)
                except:
                    pass
            
            # محاولة 3: أخذ screenshot وتحليله
            if not captcha_text:
                try:
                    screenshot = self.driver.get_screenshot_as_png()
                    img = Image.open(io.BytesIO(screenshot))
                    text = pytesseract.image_to_string(img, lang='eng')
                    match = re.search(r'(\d+)\s*\+\s*(\d+)', text)
                    if match:
                        captcha_text = match.group(0)
                except:
                    pass
            
            if captcha_text:
                logger.info(f"تم العثور على الكابتشا: {captcha_text}")
                # استخراج الأرقام وحساب النتيجة
                numbers = re.findall(r'\d+', captcha_text)
                if len(numbers) >= 2:
                    result = int(numbers[0]) + int(numbers[1])
                    logger.info(f"نتيجة الكابتشا: {result}")
                    return result
            
            # إذا فشلت جميع المحاولات، نجرب أرقام عشوائية
            logger.warning("لم يتم العثور على الكابتشا، سيتم تجربة حل افتراضي")
            return None
            
        except Exception as e:
            logger.error(f"خطأ في حل الكابتشا: {e}")
            return None
    
    def login(self):
        """تسجيل الدخول إلى الموقع"""
        try:
            logger.info("بدء عملية تسجيل الدخول...")
            self.driver.get(LOGIN_URL)
            time.sleep(3)
            
            # حفظ screenshot للتشخيص
            self.driver.save_screenshot('login_page.png')
            logger.info("تم حفظ screenshot لصفحة تسجيل الدخول")
            
            # البحث عن حقل اسم المستخدم
            try:
                username_field = WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "Username"))
                )
                logger.info("تم العثور على حقل Username")
            except:
                username_field = self.driver.find_element(By.NAME, "Username")
            
            # البحث عن حقل كلمة المرور
            try:
                password_field = self.driver.find_element(By.ID, "Password")
                logger.info("تم العثور على حقل Password")
            except:
                password_field = self.driver.find_element(By.NAME, "Password")
            
            # إدخال البيانات
            username_field.clear()
            username_field.send_keys(SITE_USERNAME)
            time.sleep(0.5)
            
            password_field.clear()
            password_field.send_keys(SITE_PASSWORD)
            time.sleep(0.5)
            
            logger.info("تم إدخال اسم المستخدم وكلمة المرور")
            
            # حل الكابتشا
            captcha_result = self.solve_captcha()
            
            if captcha_result is not None:
                # البحث عن حقل الكابتشا
                captcha_fields = self.driver.find_elements(By.TAG_NAME, "input")
                captcha_input = None
                
                for field in captcha_fields:
                    field_type = field.get_attribute("type")
                    field_name = field.get_attribute("name")
                    field_id = field.get_attribute("id")
                    
                    # البحث عن حقل يشبه حقل الكابتشا
                    if (field_type == "text" or field_type == "number") and \
                       (not field_name or "captcha" in field_name.lower() or 
                        not field_id or "captcha" in field_id.lower() or
                        field != username_field and field != password_field):
                        captcha_input = field
                        break
                
                if captcha_input:
                    captcha_input.clear()
                    captcha_input.send_keys(str(captcha_result))
                    logger.info(f"تم إدخال نتيجة الكابتشا: {captcha_result}")
                else:
                    logger.warning("لم يتم العثور على حقل الكابتشا")
            else:
                logger.warning("فشل في حل الكابتشا - سيتم المحاولة بدونها")
            
            time.sleep(1)
            
            # البحث عن زر تسجيل الدخول والنقر عليه
            try:
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            except:
                login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'تسجيل')]")
            
            login_button.click()
            logger.info("تم النقر على زر تسجيل الدخول")
            
            time.sleep(5)
            
            # حفظ screenshot بعد تسجيل الدخول
            self.driver.save_screenshot('after_login.png')
            
            # التحقق من نجاح تسجيل الدخول
            current_url = self.driver.current_url
            page_source = self.driver.page_source.lower()
            
            logger.info(f"URL الحالي: {current_url}")
            
            # علامات نجاح تسجيل الدخول
            success_indicators = [
                "dashboard" in current_url.lower(),
                "home" in current_url.lower(),
                "users" in current_url.lower(),
                "dashboard" in page_source,
                "logout" in page_source,
                "تسجيل خروج" in page_source,
                current_url != LOGIN_URL
            ]
            
            if any(success_indicators):
                logger.info("✅ تم تسجيل الدخول بنجاح")
                return True
            else:
                logger.error("❌ فشل تسجيل الدخول")
                # البحث عن رسالة خطأ
                try:
                    error_msg = self.driver.find_element(By.CLASS_NAME, "error")
                    logger.error(f"رسالة الخطأ: {error_msg.text}")
                except:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل الدخول: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return False
    
    def create_trial(self, username):
        """إنشاء حساب تجريبي"""
        try:
            logger.info(f"بدء إنشاء حساب تجريبي للمستخدم: {username}")
            self.driver.get(ADD_M3U_URL)
            time.sleep(3)
            
            # إدخال اسم المستخدم
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "Username"))
            )
            username_field.clear()
            username_field.send_keys(username)
            logger.info("تم إدخال اسم المستخدم")
            
            time.sleep(1)
            
            # اختيار Package (1day/trial/mr)
            try:
                package_select = Select(self.driver.find_element(By.ID, "PackageId"))
                # البحث عن الخيار الصحيح
                for option in package_select.options:
                    if "trial" in option.text.lower() or "528" in option.get_attribute("value"):
                        package_select.select_by_value(option.get_attribute("value"))
                        logger.info(f"تم اختيار الباقة: {option.text}")
                        break
            except Exception as e:
                logger.warning(f"تعذر اختيار الباقة: {e}")
            
            time.sleep(2)
            
            # الانتظار حتى يتم تحميل الباقات
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "SelectedBouquets"))
            )
            
            # نقل الباقات المحددة
            logger.info("بدء نقل الباقات...")
            for bouquet_id in SELECTED_BOUQUETS:
                try:
                    # تنفيذ JavaScript لتحديد ونقل الخيار
                    script = f"""
                    var allBouquets = document.getElementById('AllBouquets');
                    var option = allBouquets.querySelector('option[value="{bouquet_id}"]');
                    if (option) {{
                        option.selected = true;
                        right();
                    }}
                    """
                    self.driver.execute_script(script)
                    time.sleep(0.5)
                    logger.info(f"تم نقل الباقة: {bouquet_id}")
                except Exception as e:
                    logger.warning(f"تعذر إضافة الباقة {bouquet_id}: {e}")
            
            time.sleep(2)
            
            # تحديد جميع الخيارات في SelectedBouquets قبل الإرسال
            self.driver.execute_script("""
                var selectedBouquets = document.getElementById('SelectedBouquets');
                for (var i = 0; i < selectedBouquets.options.length; i++) {
                    selectedBouquets.options[i].selected = true;
                }
            """)
            
            logger.info("تم تحديد جميع الباقات المختارة")
            
            time.sleep(1)
            
            # حفظ screenshot قبل الإرسال
            self.driver.save_screenshot('before_submit.png')
            
            # النقر على زر Add
            add_button = self.driver.find_element(By.ID, "btnSend")
            add_button.click()
            logger.info("تم النقر على زر Add")
            
            time.sleep(5)
            
            # حفظ screenshot بعد الإرسال
            self.driver.save_screenshot('after_submit.png')
            
            # التحقق من النجاح
            current_url = self.driver.current_url
            page_source = self.driver.page_source
            
            # البحث عن رسالة نجاح أو معلومات الحساب
            success = False
            m3u_url = None
            
            # البحث عن URL M3U في الصفحة
            m3u_pattern = r'http[s]?://[^\s<>"]+\.m3u[8]?'
            m3u_matches = re.findall(m3u_pattern, page_source)
            if m3u_matches:
                m3u_url = m3u_matches[0]
                success = True
            
            # أو التحقق من وجود رسالة نجاح
            if "success" in page_source.lower() or "نجح" in page_source:
                success = True
            
            if success:
                account_info = {
                    "username": username,
                    "status": "تم الإنشاء بنجاح",
                    "package": "1day/trial/mr",
                    "duration": "24 ساعة",
                    "m3u_url": m3u_url
                }
                logger.info("✅ تم إنشاء الحساب بنجاح")
                return account_info
            else:
                logger.error("❌ فشل في إنشاء الحساب")
                return None
            
        except Exception as e:
            logger.error(f"خطأ في إنشاء الحساب: {e}")
            import traceback
            logger.error(traceback.format_exc())
            return None
    
    def close_driver(self):
        """إغلاق المتصفح"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("تم إغلاق المتصفح")
        except Exception as e:
            logger.error(f"خطأ في إغلاق المتصفح: {e}")

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
    
    # التحقق من صحة اسم المستخدم
    if not username or len(username) > 20:
        await update.message.reply_text("❌ اسم المستخدم غير صالح. يجب أن يكون أقل من 20 حرف.")
        return WAITING_USERNAME
    
    # التحقق من الأحرف الصالحة
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        await update.message.reply_text("❌ اسم المستخدم يجب أن يحتوي على أحرف وأرقام فقط (A-Z, 0-9, _, -)")
        return WAITING_USERNAME
    
    await update.message.reply_text("⏳ جارٍ إنشاء الحساب التجريبي... يرجى الانتظار")
    
    try:
        # تهيئة المتصفح
        if not bot_instance.init_driver():
            await update.message.reply_text("❌ فشل في تهيئة المتصفح")
            return ConversationHandler.END
        
        # تسجيل الدخول
        if not bot_instance.login():
            await update.message.reply_text("""
❌ فشل تسجيل الدخول إلى الموقع

الأسباب المحتملة:
• مشكلة في حل الكابتشا
• بيانات تسجيل الدخول غير صحيحة
• الموقع غير متاح حالياً

يرجى المحاولة مرة أخرى لاحقاً أو التواصل مع المسؤول.
            """)
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
• 🇫🇷 FRANCE VIP
• 🇪🇸 SPAIN
• 🇮🇹 ITALIA
• 🇩🇪 GERMANY VIP
• 🇮🇹 SKY ITALIA VIP
• 🏆 BEIN SPORTS ARABIA VIP+
• 🎬 ARABIC SPORTS CINEMA VIP
• 📡 DSTV
            """
            
            if account_info.get('m3u_url'):
                response += f"\n🔗 رابط M3U:\n`{account_info['m3u_url']}`"
            
            response += "\n\nاستمتع بالمشاهدة! 🍿"
            
            await update.message.reply_text(response, parse_mode='Markdown')
        else:
            await update.message.reply_text("""
❌ فشل إنشاء الحساب

الأسباب المحتملة:
• اسم المستخدم موجود بالفعل
• نفذت محاولات الإنشاء اليومية
• مشكلة في الموقع

يرجى تجربة اسم مستخدم آخر أو المحاولة لاحقاً.
            """)
        
        # إغلاق المتصفح
        bot_instance.close_driver()
        
    except Exception as e:
        logger.error(f"خطأ عام: {e}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع أثناء إنشاء الحساب. يرجى المحاولة لاحقاً.")
        bot_instance.close_driver()
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية"""
    await update.message.reply_text("تم إلغاء العملية. أرسل /start للبدء من جديد")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """معالج أمر /help"""
    help_text = """
📖 **دليل استخدام البوت**

🔹 /start - بدء إنشاء حساب تجريبي جديد
🔹 /cancel - إلغاء العملية الحالية
🔹 /help - عرض هذه الرسالة

💡 **ملاحظات:**
• الحساب التجريبي صالح لمدة 24 ساعة
• يتم اختيار الباقات الأساسية تلقائياً
• اسم المستخدم يجب أن يكون فريداً
    """
    await update.message.reply_text(help_text, parse_mode='Markdown')

def main():
    """تشغيل البوت"""
    # ضع هنا رمز البوت الخاص بك من @BotFather
    TOKEN = "YOUR_BOT_TOKEN_HERE"
    
    if TOKEN == 7867838350:AAEtPQjxEtfxIlguE56Fc2lZuJVK04kKf6U
        logger.error("⚠️ يرجى وضع Bot Token في المتغير TOKEN")
        return
    
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
    application.add_handler(CommandHandler('help', help_command))
    
    # بدء البوت
    logger.info("🤖 البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
