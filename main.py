import logging
import re
import os
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
        """تهيئة متصفح Chrome محسّن لـ Replit"""
        try:
            chrome_options = Options()
            # إعدادات مهمة لـ Replit
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--disable-software-rasterizer')
            chrome_options.add_argument('--disable-extensions')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--lang=ar')
            chrome_options.add_argument('--disable-logging')
            chrome_options.add_argument('--log-level=3')
            chrome_options.add_argument('--silent')
            
            # تحسينات إضافية للذاكرة
            chrome_options.add_argument('--disable-background-networking')
            chrome_options.add_argument('--disable-background-timer-throttling')
            chrome_options.add_argument('--disable-backgrounding-occluded-windows')
            chrome_options.add_argument('--disable-breakpad')
            chrome_options.add_argument('--disable-component-extensions-with-background-pages')
            chrome_options.add_argument('--disable-features=TranslateUI,BlinkGenPropertyTrees')
            chrome_options.add_argument('--disable-ipc-flooding-protection')
            chrome_options.add_argument('--disable-renderer-backgrounding')
            chrome_options.add_argument('--enable-features=NetworkService,NetworkServiceInProcess')
            chrome_options.add_argument('--force-color-profile=srgb')
            chrome_options.add_argument('--hide-scrollbars')
            chrome_options.add_argument('--metrics-recording-only')
            chrome_options.add_argument('--mute-audio')
            
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation", "enable-logging"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            
            # محاولة استخدام Chrome المثبت في Replit
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            
            # إخفاء أن المتصفح آلي
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            self.driver.execute_cdp_cmd('Network.setUserAgentOverride', {
                "userAgent": 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            })
            
            logger.info("✅ تم تهيئة المتصفح بنجاح")
            return self.driver
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة المتصفح: {e}")
            return None
    
    def solve_captcha(self):
        """حل الكابتشا الحسابية البسيطة"""
        try:
            time.sleep(1)
            
            # البحث عن نص الكابتشا (مثل "9 + 6")
            try:
                # محاولة إيجاد العنصر الذي يحتوي على العملية الحسابية
                captcha_elements = self.driver.find_elements(By.XPATH, 
                    "//*[contains(text(), '+') or contains(text(), '-') or contains(text(), '×') or contains(text(), '÷')]")
                
                for element in captcha_elements:
                    captcha_text = element.text.strip()
                    if captcha_text:
                        logger.info(f"🔢 تم العثور على كابتشا: {captcha_text}")
                        
                        # استخراج الأرقام والعملية
                        import re
                        # البحث عن نمط مثل "9 + 6" أو "9+6"
                        match = re.search(r'(\d+)\s*([+\-×÷*\/])\s*(\d+)', captcha_text)
                        
                        if match:
                            num1 = int(match.group(1))
                            operation = match.group(2)
                            num2 = int(match.group(3))
                            
                            # حساب النتيجة
                            if operation == '+':
                                result = num1 + num2
                            elif operation == '-':
                                result = num1 - num2
                            elif operation in ['×', '*']:
                                result = num1 * num2
                            elif operation in ['÷', '/']:
                                result = num1 // num2
                            else:
                                result = None
                            
                            if result is not None:
                                logger.info(f"✅ تم حل الكابتشا: {num1} {operation} {num2} = {result}")
                                return result
                
                # إذا لم نجد الكابتشا بالطريقة العادية، نحاول البحث في الصفحة
                page_source = self.driver.page_source
                math_pattern = re.search(r'>(\d+)\s*([+\-×÷*\/])\s*(\d+)<', page_source)
                if math_pattern:
                    num1 = int(math_pattern.group(1))
                    operation = math_pattern.group(2)
                    num2 = int(math_pattern.group(3))
                    
                    if operation == '+':
                        result = num1 + num2
                    elif operation == '-':
                        result = num1 - num2
                    elif operation in ['×', '*']:
                        result = num1 * num2
                    elif operation in ['÷', '/']:
                        result = num1 // num2
                    else:
                        return None
                    
                    logger.info(f"✅ تم حل الكابتشا من الصفحة: {num1} {operation} {num2} = {result}")
                    return result
                    
            except Exception as e:
                logger.warning(f"⚠️ خطأ في قراءة الكابتشا: {e}")
            
            logger.info("ℹ️ لم يتم العثور على كابتشا")
            return None
            
        except Exception as e:
            logger.error(f"❌ خطأ في حل الكابتشا: {e}")
            return None
    
    def login(self):
        """تسجيل الدخول إلى الموقع"""
        try:
            logger.info("🔑 بدء عملية تسجيل الدخول...")
            self.driver.get(LOGIN_URL)
            time.sleep(3)
            
            # إدخال اسم المستخدم
            username_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "Username"))
            )
            username_field.clear()
            time.sleep(0.5)
            username_field.send_keys(SITE_USERNAME)
            
            # إدخال كلمة المرور
            password_field = self.driver.find_element(By.ID, "Password")
            password_field.clear()
            time.sleep(0.5)
            password_field.send_keys(SITE_PASSWORD)
            
            # محاولة حل الكابتشا
            time.sleep(2)  # انتظار تحميل الكابتشا
            captcha_result = self.solve_captcha()
            
            if captcha_result is not None:
                try:
                    # البحث عن حقل إدخال الكابتشا
                    captcha_input = None
                    
                    # محاولة 1: بواسطة ID
                    try:
                        captcha_input = self.driver.find_element(By.ID, "Captcha")
                    except:
                        pass
                    
                    # محاولة 2: بواسطة Name
                    if not captcha_input:
                        try:
                            captcha_input = self.driver.find_element(By.NAME, "Captcha")
                        except:
                            pass
                    
                    # محاولة 3: بواسطة CSS Selector
                    if not captcha_input:
                        try:
                            captcha_input = self.driver.find_element(By.CSS_SELECTOR, "input[placeholder*='captcha' i]")
                        except:
                            pass
                    
                    # محاولة 4: البحث في جميع حقول الإدخال
                    if not captcha_input:
                        inputs = self.driver.find_elements(By.TAG_NAME, "input")
                        for inp in inputs:
                            input_type = inp.get_attribute("type")
                            input_id = inp.get_attribute("id")
                            input_name = inp.get_attribute("name")
                            if input_type == "text" and (
                                (input_id and "captcha" in input_id.lower()) or 
                                (input_name and "captcha" in input_name.lower())
                            ):
                                captcha_input = inp
                                break
                    
                    if captcha_input:
                        captcha_input.clear()
                        time.sleep(0.5)
                        captcha_input.send_keys(str(captcha_result))
                        logger.info(f"✅ تم إدخال نتيجة الكابتشا: {captcha_result}")
                    else:
                        logger.warning("⚠️ لم يتم العثور على حقل إدخال الكابتشا")
                        
                except Exception as e:
                    logger.warning(f"⚠️ خطأ في إدخال الكابتشا: {e}")
            else:
                logger.warning("⚠️ لم يتم حل الكابتشا")
            
            # النقر على زر تسجيل الدخول
            try:
                login_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']"))
                )
            except:
                login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'تسجيل')]")
            
            login_button.click()
            logger.info("⏳ تم النقر على زر تسجيل الدخول...")
            
            # انتظار أطول قليلاً لإتمام عملية تسجيل الدخول
            time.sleep(8)
            
            # التحقق من نجاح تسجيل الدخول
            current_url = self.driver.current_url
            if "dashboard" in current_url.lower() or "users" in current_url.lower() or current_url != LOGIN_URL:
                logger.info("✅ تم تسجيل الدخول بنجاح")
                return True
            else:
                logger.error(f"❌ فشل تسجيل الدخول - URL الحالي: {current_url}")
                # حفظ لقطة شاشة للتشخيص
                try:
                    self.driver.save_screenshot('/tmp/login_failed.png')
                    logger.info("📸 تم حفظ لقطة شاشة في /tmp/login_failed.png")
                except:
                    pass
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الدخول: {e}")
            try:
                self.driver.save_screenshot('/tmp/login_error.png')
            except:
                pass
            return False
    
    def create_trial(self, username):
        """إنشاء حساب تجريبي"""
        try:
            logger.info(f"📝 بدء إنشاء حساب تجريبي للمستخدم: {username}")
            self.driver.get(ADD_M3U_URL)
            time.sleep(3)
            
            # إدخال اسم المستخدم
            username_field = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.ID, "Username"))
            )
            username_field.clear()
            time.sleep(0.5)
            username_field.send_keys(username)
            logger.info(f"✅ تم إدخال اسم المستخدم: {username}")
            
            # اختيار الباقة Trial
            try:
                package_select = Select(WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.ID, "PackageId"))
                ))
                for option in package_select.options:
                    if "trial" in option.text.lower() or "1day" in option.text.lower():
                        package_select.select_by_value(option.get_attribute("value"))
                        logger.info(f"✅ تم اختيار الباقة: {option.text}")
                        break
            except Exception as e:
                logger.warning(f"⚠️ تعذر اختيار الباقة: {e}")
            
            time.sleep(2)
            
            # اختيار الباقات (Bouquets)
            logger.info("📦 بدء اختيار الباقات...")
            for bouquet_id in SELECTED_BOUQUETS:
                try:
                    script = f"""
                    var allBouquets = document.getElementById('AllBouquets');
                    if (allBouquets) {{
                        var option = allBouquets.querySelector('option[value="{bouquet_id}"]');
                        if (option) {{
                            option.selected = true;
                            if (typeof right === 'function') {{
                                right();
                            }}
                        }}
                    }}
                    """
                    self.driver.execute_script(script)
                    time.sleep(0.5)
                    logger.info(f"✅ تم إضافة الباقة: {bouquet_id}")
                except Exception as e:
                    logger.warning(f"⚠️ فشل إضافة الباقة {bouquet_id}: {e}")
            
            # تحديد جميع الباقات المختارة
            time.sleep(1)
            self.driver.execute_script("""
                var selectedBouquets = document.getElementById('SelectedBouquets');
                if (selectedBouquets) {
                    for (var i = 0; i < selectedBouquets.options.length; i++) {
                        selectedBouquets.options[i].selected = true;
                    }
                }
            """)
            
            # النقر على زر Add/Submit
            try:
                add_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.ID, "btnSend"))
                )
                add_button.click()
                logger.info("✅ تم النقر على زر الإضافة")
            except Exception as e:
                logger.error(f"❌ لم يتم العثور على زر Add: {e}")
                try:
                    add_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
                    add_button.click()
                except:
                    pass
            
            time.sleep(5)
            
            # البحث عن رابط M3U في الصفحة
            page_source = self.driver.page_source
            m3u_pattern = r'http[s]?://[^\s<>"]+\.m3u[8]?'
            m3u_matches = re.findall(m3u_pattern, page_source)
            
            if m3u_matches:
                m3u_url = m3u_matches[0]
                logger.info(f"✅ تم العثور على رابط M3U: {m3u_url}")
                return {
                    "username": username,
                    "package": "1day/trial",
                    "duration": "24 ساعة",
                    "m3u_url": m3u_url
                }
            else:
                logger.error("❌ لم يتم العثور على رابط M3U")
                # حفظ الصفحة للتشخيص
                try:
                    with open('/tmp/page_source.html', 'w', encoding='utf-8') as f:
                        f.write(page_source)
                    logger.info("📄 تم حفظ محتوى الصفحة في /tmp/page_source.html")
                except:
                    pass
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء الحساب: {e}")
            try:
                self.driver.save_screenshot('/tmp/create_error.png')
            except:
                pass
            return None
    
    def close_driver(self):
        """إغلاق المتصفح وتنظيف الموارد"""
        try:
            if self.driver:
                self.driver.quit()
                logger.info("✅ تم إغلاق المتصفح بنجاح")
        except Exception as e:
            logger.error(f"⚠️ خطأ في إغلاق المتصفح: {e}")

# متغير عام للبوت
bot_instance = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """أمر البدء"""
    welcome_message = """
🎬 مرحباً بك في بوت إنشاء Trial M3U

🔹 للحصول على حساب تجريبي لمدة 24 ساعة
🔹 أرسل اسم المستخدم الذي تريده (أحرف وأرقام فقط)

📌 مثال: user123
"""
    await update.message.reply_text(welcome_message)
    return WAITING_USERNAME

async def create_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إنشاء الحساب التجريبي"""
    global bot_instance
    username = update.message.text.strip()
    
    # التحقق من صحة اسم المستخدم
    if not re.match(r'^[a-zA-Z0-9_-]{3,20}$', username):
        await update.message.reply_text(
            "❌ اسم المستخدم غير صالح!\n\n"
            "يجب أن يحتوي على:\n"
            "• أحرف وأرقام فقط (a-z, A-Z, 0-9)\n"
            "• من 3 إلى 20 حرف\n"
            "• يمكن استخدام _ و -"
        )
        return WAITING_USERNAME
    
    await update.message.reply_text("⏳ جارٍ إنشاء الحساب التجريبي...\nقد يستغرق هذا بضع ثوانٍ...")

    try:
        # إنشاء instance جديد من البوت
        bot_instance = M3UBot()
        
        # تهيئة المتصفح
        if not bot_instance.init_driver():
            await update.message.reply_text("❌ فشل في تهيئة المتصفح.\nالرجاء المحاولة مرة أخرى لاحقاً.")
            return ConversationHandler.END

        # تسجيل الدخول
        if not bot_instance.login():
            await update.message.reply_text(
                "❌ فشل تسجيل الدخول إلى الموقع.\n"
                "قد يكون هناك مشكلة في الكابتشا أو بيانات الدخول."
            )
            bot_instance.close_driver()
            return ConversationHandler.END

        # إنشاء الحساب
        account_info = bot_instance.create_trial(username)

        if account_info:
            response = f"""
✅ تم إنشاء الحساب بنجاح!

━━━━━━━━━━━━━━━━━━
👤 اسم المستخدم: {account_info['username']}
📦 الباقة: {account_info['package']}
⏱ المدة: {account_info['duration']}
━━━━━━━━━━━━━━━━━━

🔗 رابط M3U:
{account_info['m3u_url']}

━━━━━━━━━━━━━━━━━━
💡 استخدم الرابط في تطبيق IPTV المفضل لديك
"""
            await update.message.reply_text(response)
        else:
            await update.message.reply_text(
                "❌ فشل إنشاء الحساب.\n"
                "قد يكون اسم المستخدم مستخدماً بالفعل أو حدث خطأ في النظام."
            )

    except Exception as e:
        logger.error(f"❌ خطأ عام: {e}")
        await update.message.reply_text("❌ حدث خطأ غير متوقع. الرجاء المحاولة مرة أخرى.")
    
    finally:
        # إغلاق المتصفح في جميع الحالات
        if bot_instance:
            bot_instance.close_driver()
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """إلغاء العملية"""
    await update.message.reply_text("❌ تم إلغاء العملية.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """عرض التعليمات"""
    help_text = """
📖 تعليمات الاستخدام:

/start - بدء البوت والحصول على حساب تجريبي
/help - عرض هذه التعليمات
/cancel - إلغاء العملية الحالية

━━━━━━━━━━━━━━━━━━
ℹ️ معلومات مهمة:
• الحساب التجريبي صالح لمدة 24 ساعة
• اسم المستخدم يجب أن يكون فريداً
• استخدم أحرف وأرقام فقط في اسم المستخدم
"""
    await update.message.reply_text(help_text)

def main():
    """الدالة الرئيسية"""
    # استخدام التوكن المقدم
    TOKEN = "7867838350:AAEtPQjxEtfxIlguE56Fc2lZuJVK04kKf6U"
    
    # يمكن أيضاً استخدام متغيرات البيئة (أفضل للأمان)
    # TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', TOKEN)
    
    if not TOKEN or TOKEN == "ضع_رمز_البوت_هنا":
        logger.error("⚠️ خطأ: لم يتم تعيين توكن البوت!")
        print("⚠️ الرجاء تعيين توكن البوت في المتغير TOKEN")
        return
    
    try:
        # إنشاء التطبيق
        application = Application.builder().token(TOKEN).build()
        
        # إعداد معالج المحادثة
        conv_handler = ConversationHandler(
            entry_points=[CommandHandler('start', start)],
            states={
                WAITING_USERNAME: [
                    MessageHandler(filters.TEXT & ~filters.COMMAND, create_account)
                ]
            },
            fallbacks=[CommandHandler('cancel', cancel)],
        )
        
        # إضافة المعالجات
        application.add_handler(conv_handler)
        application.add_handler(CommandHandler('help', help_command))
        
        # بدء البوت
        logger.info("=" * 50)
        logger.info("🤖 البوت يعمل الآن...")
        logger.info("✅ جاهز لاستقبال الطلبات")
        logger.info("=" * 50)
        
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
        
    except Exception as e:
        logger.error(f"❌ خطأ في تشغيل البوت: {e}")
        print(f"❌ خطأ: {e}")

if __name__ == '__main__':
    main()
