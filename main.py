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
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-blink-features=AutomationControlled')
            chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
            chrome_options.add_experimental_option('useAutomationExtension', False)
            chrome_options.add_argument('--window-size=1920,1080')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--lang=ar')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=chrome_options)
            self.driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
            
            logger.info("تم تهيئة المتصفح بنجاح")
            return self.driver
        except Exception as e:
            logger.error(f"خطأ في تهيئة المتصفح: {e}")
            return None
    
    def solve_captcha(self):
        """حل الكابتشا (تم تعطيله مؤقتاً)"""
        logger.info("تخطي الكابتشا في وضع Replit")
        return 5  # رقم افتراضي
    
    def login(self):
        """تسجيل الدخول إلى الموقع"""
        try:
            logger.info("بدء عملية تسجيل الدخول...")
            self.driver.get(LOGIN_URL)
            time.sleep(3)
            
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "Username"))
            )
            password_field = self.driver.find_element(By.ID, "Password")
            
            username_field.clear()
            username_field.send_keys(SITE_USERNAME)
            password_field.clear()
            password_field.send_keys(SITE_PASSWORD)
            
            captcha_result = self.solve_captcha()
            if captcha_result:
                try:
                    captcha_input = self.driver.find_element(By.ID, "Captcha")
                    captcha_input.clear()
                    captcha_input.send_keys(str(captcha_result))
                except:
                    pass
            
            try:
                login_button = self.driver.find_element(By.CSS_SELECTOR, "button[type='submit']")
            except:
                login_button = self.driver.find_element(By.XPATH, "//button[contains(text(), 'Login') or contains(text(), 'تسجيل')]")
            
            login_button.click()
            logger.info("تم النقر على زر تسجيل الدخول")
            time.sleep(5)
            
            current_url = self.driver.current_url
            if "dashboard" in current_url.lower() or "users" in current_url.lower() or current_url != LOGIN_URL:
                logger.info("✅ تم تسجيل الدخول بنجاح")
                return True
            else:
                logger.error("❌ فشل تسجيل الدخول")
                return False
                
        except Exception as e:
            logger.error(f"خطأ في تسجيل الدخول: {e}")
            return False
    
    def create_trial(self, username):
        """إنشاء حساب تجريبي"""
        try:
            logger.info(f"بدء إنشاء حساب تجريبي للمستخدم: {username}")
            self.driver.get(ADD_M3U_URL)
            time.sleep(3)
            
            username_field = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "Username"))
            )
            username_field.clear()
            username_field.send_keys(username)
            
            try:
                package_select = Select(self.driver.find_element(By.ID, "PackageId"))
                for option in package_select.options:
                    if "trial" in option.text.lower():
                        package_select.select_by_value(option.get_attribute("value"))
                        break
            except Exception as e:
                logger.warning(f"تعذر اختيار الباقة: {e}")
            
            time.sleep(2)
            
            for bouquet_id in SELECTED_BOUQUETS:
                try:
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
                except:
                    pass
            
            self.driver.execute_script("""
                var selectedBouquets = document.getElementById('SelectedBouquets');
                for (var i = 0; i < selectedBouquets.options.length; i++) {
                    selectedBouquets.options[i].selected = true;
                }
            """)
            
            try:
                add_button = self.driver.find_element(By.ID, "btnSend")
                add_button.click()
            except:
                logger.error("لم يتم العثور على زر Add")
            
            time.sleep(5)
            page_source = self.driver.page_source
            m3u_pattern = r'http[s]?://[^\s<>"]+\.m3u[8]?'
            m3u_matches = re.findall(m3u_pattern, page_source)
            m3u_url = m3u_matches[0] if m3u_matches else None
            
            if m3u_url:
                return {
                    "username": username,
                    "package": "1day/trial",
                    "duration": "24 ساعة",
                    "m3u_url": m3u_url
                }
            else:
                return None
        except Exception as e:
            logger.error(f"خطأ في إنشاء الحساب: {e}")
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
    welcome_message = """
🎬 مرحباً بك في بوت إنشاء Trial M3U

للحصول على حساب تجريبي لمدة 24 ساعة، أرسل اسم المستخدم الذي تريده.
"""
    await update.message.reply_text(welcome_message)
    return WAITING_USERNAME

async def create_account(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    if not re.match(r'^[a-zA-Z0-9_-]+$', username):
        await update.message.reply_text("❌ اسم المستخدم يجب أن يحتوي على أحرف وأرقام فقط.")
        return WAITING_USERNAME
    
    await update.message.reply_text("⏳ جارٍ إنشاء الحساب التجريبي...")

    if not bot_instance.init_driver():
        await update.message.reply_text("❌ فشل في تهيئة المتصفح.")
        return ConversationHandler.END

    if not bot_instance.login():
        await update.message.reply_text("❌ فشل تسجيل الدخول إلى الموقع.")
        bot_instance.close_driver()
        return ConversationHandler.END

    account_info = bot_instance.create_trial(username)

    if account_info:
        response = f"""
✅ تم إنشاء الحساب بنجاح!

👤 اسم المستخدم: {account_info['username']}
📦 الباقة: {account_info['package']}
⏱ المدة: {account_info['duration']}

🔗 رابط M3U:
{account_info['m3u_url']}
"""
        await update.message.reply_text(response)
    else:
        await update.message.reply_text("❌ فشل إنشاء الحساب.")

    bot_instance.close_driver()
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("تم إلغاء العملية.")
    return ConversationHandler.END

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("/start - بدء\n/help - تعليمات")

def main():
    TOKEN = "ضع_رمز_البوت_هنا"  # ← استبدل هذا بالتوكن الحقيقي من BotFather
    
    if TOKEN == "ضع_رمز_البوت_هنا":
        logger.error("⚠️ لم يتم وضع توكن البوت بعد.")
        return
    
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={WAITING_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, create_account)]},
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler('help', help_command))
    
    logger.info("🤖 البوت يعمل الآن...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
