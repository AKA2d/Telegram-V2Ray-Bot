# All customer-facing and admin-facing copy lives here in Persian.

MAIN_MENU_BUY = "🛒 خرید سرویس"
MAIN_MENU_MANAGE = "⚙️ مدیریت سرویس"
MAIN_MENU_ACCOUNT = "👤 اطلاعات حساب"
MAIN_MENU_TOPUP = "💳 شارژ حساب"
MAIN_MENU_CONNECT = "📱 روش اتصال"

BTN_CONFIRM = "بله ✅"
BTN_CANCEL = "خیر ❌"
BTN_BACK = "🔙 بازگشت"
BTN_CANCEL_FLOW = "لغو"
BTN_NEXT_CARD = "💳 کارت بعدی"
BTN_APPROVE = "✅ تایید"
BTN_REJECT = "❌ رد"

WELCOME = "به ربات فروش سرویس V2Ray خوش آمدید 👋\nاز منوی زیر یکی از گزینه‌ها را انتخاب کنید:"

JOIN_CHANNEL_PROMPT = "برای استفاده از ربات ابتدا باید عضو کانال ما شوید."
JOIN_CHANNEL_BUTTON = "عضویت در کانال"
CHECK_MEMBERSHIP_BUTTON = "✅ عضو شدم"
NOT_MEMBER_YET = "شما هنوز عضو کانال نشده‌اید. لطفا ابتدا عضو شوید."

ASK_USER_COUNT = "تعداد کاربر مورد نظر خود را وارد کنید (عدد):"
ASK_MONTHS = "مدت زمان سرویس را به ماه وارد کنید (عدد):"
ASK_TRAFFIC = "میزان ترافیک مورد نیاز را به گیگابایت وارد کنید (عدد):"
INVALID_NUMBER = "لطفا یک عدد معتبر و بزرگ‌تر از صفر وارد کنید."

ORDER_SUMMARY = (
    "خلاصه سفارش شما:\n\n"
    "👥 تعداد کاربر: {user_count}\n"
    "📅 مدت: {months} ماه\n"
    "🌐 ترافیک: {traffic_gb} گیگابایت\n"
    "💰 مبلغ قابل پرداخت: {price} تومان\n\n"
    "آیا سفارش را تایید می‌کنید؟"
)

ORDER_CREATED = (
    "سرویس شما با موفقیت ساخته شد ✅ (غیرفعال تا زمان تایید پرداخت)\n\n"
    "🔗 لینک اشتراک شما:\n{link}\n\n"
    "⚠️ این لینک تا تایید پرداخت توسط ادمین فعال نخواهد شد."
)

PAYMENT_INSTRUCTIONS = (
    "لطفا مبلغ {amount} تومان را به شماره کارت زیر واریز کنید:\n\n"
    "💳 {card_number}\n{holder_name}\n\n"
    "در صورت غیرفعال بودن یا پر بودن ظرفیت این کارت، از دکمه «کارت بعدی» استفاده کنید.\n"
    "سپس رسید پرداخت (متن یا عکس) را ارسال کنید."
)

NO_ACTIVE_CARD = "در حال حاضر کارتی برای پرداخت ثبت نشده است. لطفا با ادمین تماس بگیرید."
NO_MORE_CARDS = "کارت دیگری موجود نیست."

RECEIPT_RECEIVED = "رسید شما دریافت شد و برای بررسی به ادمین ارسال گردید. لطفا منتظر تایید بمانید."

NEW_ORDER_ADMIN_NOTICE = (
    "📥 سفارش جدید\n\n"
    "نوع: {order_type}\n"
    "کاربر: {user_display}\n"
    "آیدی عددی: {telegram_id}\n"
    "لینک ارتباط مستقیم: {deep_link}\n"
    "مبلغ: {amount} تومان\n"
    "کارت استفاده‌شده: {card}\n"
)

ORDER_APPROVED_CUSTOMER = "پرداخت شما تایید شد ✅"
SERVICE_ACTIVATED_CUSTOMER = "سرویس شما فعال شد 🎉\n\n🔗 لینک اشتراک شما:\n{link}"
WALLET_TOPUP_APPROVED_CUSTOMER = "شارژ کیف پول شما تایید شد. موجودی جدید: {balance} تومان"
ORDER_REJECTED_CUSTOMER = "متاسفانه سفارش شما توسط ادمین رد شد. برای اطلاعات بیشتر با پشتیبانی تماس بگیرید."

ORDER_ALREADY_PROCESSED = "این سفارش قبلا بررسی شده است."

MANAGE_SERVICE_PROMPT = "لینک اشتراک، شناسه سرویس یا از لیست زیر سرویس مورد نظر را انتخاب کنید:"
NO_SERVICES = "شما هنوز هیچ سرویسی ثبت نکرده‌اید."
SERVICE_NOT_FOUND = "سرویسی با این مشخصات پیدا نشد."

SERVICE_DETAIL = (
    "📦 سرویس #{id}\n"
    "وضعیت: {status}\n"
    "تعداد کاربر: {user_count}\n"
    "مدت: {months} ماه\n"
    "ترافیک: {traffic_gb} گیگابایت\n"
    "تاریخ ساخت: {created_at}\n\n"
    "🔗 لینک اشتراک:\n{link}"
)

BTN_REGENERATE = "🔄 تغییر لینک ساب"
BTN_INCREASE_USERS = "➕ افزایش تعداد کاربر"
BTN_EXTEND = "⏳ تمدید سرویس"

REGENERATE_DONE = "لینک اشتراک با موفقیت تغییر کرد:\n{link}"
PHASE2_NOT_AVAILABLE = "این قابلیت به زودی فعال می‌شود."

ACCOUNT_INFO = (
    "👤 اطلاعات حساب شما:\n\n"
    "تعداد کل سرویس‌های خریداری‌شده: {total_services}\n"
    "تعداد سرویس‌های فعال: {active_services}\n"
    "موجودی کیف پول: {wallet_balance} تومان"
)

ASK_TOPUP_AMOUNT = "مبلغی که می‌خواهید به کیف پول اضافه کنید را به تومان وارد کنید:"

CONNECT_CHOOSE_PLATFORM = "پلتفرم خود را انتخاب کنید:"
CONNECT_PLATFORM_IOS = "📱 آیفون"
CONNECT_PLATFORM_ANDROID = "🤖 اندروید"
CONNECT_CHOOSE_APP = "یکی از اپلیکیشن‌های زیر را انتخاب کنید:"

CANCELLED = "عملیات لغو شد."
ERROR_GENERIC = "خطایی رخ داد. لطفا دوباره تلاش کنید یا با پشتیبانی تماس بگیرید."
PANEL_ERROR_ADMIN = "⚠️ خطا در ارتباط با پنل:\n{error}"

# ---- Admin -----------------------------------------------------------------

ADMIN_MENU = "پنل مدیریت"
ADMIN_MENU_ORDERS = "📥 بررسی سفارش‌ها"
ADMIN_MENU_PRICING = "💰 مدیریت قیمت‌گذاری"
ADMIN_MENU_CUSTOMERS = "🔍 جستجوی مشتری"
ADMIN_MENU_WALLET = "💳 تغییر موجودی کیف پول"
ADMIN_MENU_BROADCAST = "📢 پیام همگانی"
ADMIN_MENU_DIRECT = "✉️ پیام به شخص خاص"
ADMIN_MENU_CARDS = "🏦 مدیریت کارت‌ها"
ADMIN_MENU_TUNNEL = "🚇 مدیریت تانل"

NOT_AUTHORIZED = "شما به این بخش دسترسی ندارید."

NO_PENDING_ORDERS = "سفارش در حال بررسی وجود ندارد."

ASK_PRICE_PER_USER = "قیمت هر کاربر اضافه (به تومان) را وارد کنید:"
ASK_PRICE_PER_MONTH = "قیمت هر ماه (به تومان) را وارد کنید:"
ASK_PRICE_PER_GB = "قیمت هر گیگابایت ترافیک (به تومان) را وارد کنید:"
ASK_BASE_PRICE = "قیمت پایه سرویس (به تومان) را وارد کنید:"
PRICING_UPDATED = "قیمت‌گذاری با موفقیت بروزرسانی شد."
PRICING_CURRENT = (
    "قیمت‌گذاری فعلی:\n\n"
    "قیمت پایه: {base_price} تومان\n"
    "هر کاربر اضافه: {price_per_user} تومان\n"
    "هر ماه: {price_per_month} تومان\n"
    "هر گیگابایت: {price_per_gb} تومان"
)

ASK_CUSTOMER_QUERY = "آیدی عددی، یوزرنیم تلگرام، یوزرنیم پنل یا UUID مشتری را وارد کنید:"
CUSTOMER_NOT_FOUND = "مشتری پیدا نشد."
CUSTOMER_PROFILE = (
    "👤 پروفایل مشتری\n\n"
    "آیدی عددی: {telegram_id}\n"
    "یوزرنیم: @{username}\n"
    "موجودی کیف پول: {wallet_balance} تومان\n"
    "تعداد سرویس: {service_count}\n"
    "تعداد سفارش: {order_count}\n\n"
    "لینک ارتباط مستقیم: {deep_link}"
)

ASK_WALLET_NEW_BALANCE = "موجودی جدید کیف پول این کاربر را به تومان وارد کنید:"
CONFIRM_WALLET_CHANGE = "آیا مطمئن هستید که می‌خواهید موجودی کاربر {telegram_id} را از {old} به {new} تومان تغییر دهید؟"
WALLET_CHANGE_DONE = "موجودی کیف پول با موفقیت تغییر کرد."
WALLET_NEGATIVE_ERROR = "موجودی کیف پول نمی‌تواند منفی باشد."

ASK_BROADCAST_TEXT = "متن پیام همگانی را ارسال کنید:"
BROADCAST_STARTED = "ارسال پیام همگانی آغاز شد..."
BROADCAST_PROGRESS = "ارسال شده: {sent}/{total} (خطا: {failed})"
BROADCAST_DONE = "پیام همگانی برای {sent} نفر از {total} کاربر با موفقیت ارسال شد."

ASK_DIRECT_TARGET = "آیدی عددی یا یوزرنیم مشتری مورد نظر برای ارسال پیام مستقیم را وارد کنید:"
ASK_DIRECT_TEXT = "متن پیام را وارد کنید:"
DIRECT_MESSAGE_SENT = "پیام با موفقیت ارسال شد."
DIRECT_MESSAGE_FAILED = "ارسال پیام ناموفق بود (ممکن است کاربر ربات را بلاک کرده باشد)."

ASK_CARD_NUMBER = "شماره کارت جدید را وارد کنید:"
ASK_CARD_HOLDER = "نام صاحب کارت را وارد کنید:"
CARD_ADDED = "کارت با موفقیت اضافه شد."
CARD_REMOVED = "کارت حذف شد."
CARD_ACTIVATED = "کارت به عنوان کارت فعال انتخاب شد."
NO_CARDS = "هیچ کارتی ثبت نشده است."

ASK_TUNNEL_TARGET = "یوزرنیم/UUID حساب مورد نظر یا 'همه' برای اعمال روی همه حساب‌ها را وارد کنید:"
TUNNEL_ADDED = "تانل با موفقیت اضافه شد."
TUNNEL_REMOVED = "تانل با موفقیت حذف شد."
