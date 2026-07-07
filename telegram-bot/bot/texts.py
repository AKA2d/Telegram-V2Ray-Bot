# All customer-facing and admin-facing copy lives here in Persian.

MAIN_MENU_BUY = "🛒 خرید سرویس"
MAIN_MENU_MANAGE = "⚙️ مدیریت سرویس"
MAIN_MENU_ACCOUNT = "👤 اطلاعات حساب"
MAIN_MENU_TOPUP = "💳 شارژ حساب"
MAIN_MENU_CONNECT = "📱 روش اتصال"
MAIN_MENU_SUPPORT = "💬 پشتیبانی"

BTN_CONFIRM = "بله ✅"
BTN_CANCEL = "خیر ❌"
BTN_BACK = "🔙 بازگشت"
BTN_CANCEL_FLOW = "لغو"
BTN_NEXT_CARD = "💳 کارت بعدی"
BTN_APPROVE = "✅ تایید"
BTN_REJECT = "❌ رد"

WELCOME = "به ربات فروش God VPN خوش آمدید 👋\nاز منوی زیر یکی از گزینه‌ها را انتخاب کنید:"

JOIN_CHANNEL_PROMPT = "برای استفاده از ربات ابتدا باید عضو کانال ما شوید."
JOIN_CHANNEL_BUTTON = "عضویت در کانال"
CHECK_MEMBERSHIP_BUTTON = "✅ عضو شدم"
NOT_MEMBER_YET = "شما هنوز عضو کانال نشده‌اید. لطفا ابتدا عضو شوید."

INVALID_NUMBER = "لطفا یک عدد معتبر و بزرگ‌تر از صفر وارد کنید."

CHOOSE_PLAN_PROMPT = "لطفا یکی از پلن‌های زیر را انتخاب کنید:"
NO_PLANS_AVAILABLE = "در حال حاضر پلنی برای فروش تعریف نشده است. لطفا با ادمین تماس بگیرید."
PLAN_NOT_FOUND = "پلن انتخابی پیدا نشد. لطفا دوباره تلاش کنید."
CONFIRM_YES = "✅ بله، مطمئنم"
CONFIRM_NO = "❌ خیر، انصراف"
PLAN_PURCHASE_CANCELLED = "خرید لغو شد."
WALLET_PAYMENT_SUCCESS = (
    "پرداخت از کیف پول با موفقیت انجام شد ✅\n\n"
    "🔗 لینک اشتراک شما:\n{link}\n\n"
    "سرویس شما اکنون فعال است."
)

ORDER_SUMMARY = (
    "خلاصه سفارش شما:\n\n"
    "📦 پلن: {plan_name}\n"
    "🧑‍🤝‍🧑 تعداد کاربر: نامحدود\n"
    "📅 مدت: {months} ماه\n"
    "🌐 ترافیک: {traffic_gb} گیگابایت\n"
    "💰 مبلغ قابل پرداخت: {price} تومان\n\n"
    "آیا سفارش را تایید می‌کنید؟"
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
ADMIN_MENU_PLANS = "📦 مدیریت پلن‌ها"
ADMIN_MENU_CUSTOMERS = "🔍 جستجوی مشتری"
ADMIN_MENU_WALLET = "💳 تغییر موجودی کیف پول"
ADMIN_MENU_BROADCAST = "📢 پیام همگانی"
ADMIN_MENU_DIRECT = "✉️ پیام به شخص خاص"
ADMIN_MENU_CARDS = "🏦 مدیریت کارت‌ها"
ADMIN_MENU_TUNNEL = "🚇 مدیریت تانل"
ADMIN_MENU_WHOLESALERS = "🛍️ مدیریت عمده‌فروشان"

SALES_CLOSED_ON = "فروش بسته شد. کاربران دیگر قادر به خرید یا شارژ نیستند."
SALES_CLOSED_OFF = "فروش باز شد."
SALES_CLOSEDMsg = "فروش در حال حاضر بسته است. لطفاً بعداً تلاش کنید."
SALES_CLOSED_LABEL_ON = "🟢 فروش: باز"
SALES_CLOSED_LABEL_OFF = "🔴 فروش: بسته"

WHOLESALER_MENU_HEADER = "مدیریت عمده‌فروشان"
NO_WHOLESALERS_DEFINED = "هیچ عمده‌فروشی تعریف نشده است."
ASK_WHOLESALER_TELEGRAM_ID = "شناسه عددی تلگرام عمده‌فروش را ارسال کنید:"
WHOLESALER_ADDED = "عمده‌فروش با موفقیت اضافه شد."
WHOLESALER_REMOVED = "عمده‌فروش حذف شد."
WHOLESALER_NOT_FOUND = "عمده‌فروش پیدا نشد. لطفا شناسه معتبر ارسال کنید."

NOT_AUTHORIZED = "شما به این بخش دسترسی ندارید. \n برای بازگشت به منوی اصلی. \n /start"

NO_PENDING_ORDERS = "سفارش در حال بررسی وجود ندارد."

NO_PLANS_DEFINED = "هیچ پلنی تعریف نشده است."
PLANS_LIST_HEADER = "پلن‌های تعریف‌شده:"
ASK_PLAN_NAME = "نام پلن را وارد کنید (مثلا «۱ کاربر - ۱ ماهه»):"
ASK_PLAN_USER_COUNT = "تعداد کاربر این پلن را وارد کنید (عدد):"
ASK_PLAN_MONTHS = "مدت این پلن را به ماه وارد کنید (عدد):"
ASK_PLAN_TRAFFIC = "ترافیک این پلن را به گیگابایت وارد کنید (عدد):"
ASK_PLAN_PRICE = "قیمت این پلن را به تومان وارد کنید (عدد):"
ASK_PLAN_WHOLESALE_PRICE = "قیمت عمده‌فروشی این پلن را به تومان وارد کنید (عدد یا '-' برای استفاده از قیمت عادی):"
PLAN_ADDED = "پلن با موفقیت اضافه شد."
PLAN_REMOVED = "پلن حذف شد."
PLAN_TOGGLED = "وضعیت پلن تغییر کرد."
PLAN_EDIT_CHOOSE_FIELD = "کدام فیلد پلن «{name}» را می‌خواهید تغییر دهید؟"
PLAN_FIELD_UPDATED = "فیلد با موفقیت به‌روزرسانی شد."
PLAN_EDIT_NAME = "نام جدید پلن را وارد کنید:"
PLAN_EDIT_USER_COUNT = "تعداد کاربر جدید را وارد کنید:"
PLAN_EDIT_MONTHS = "مدت جدید (ماه) را وارد کنید:"
PLAN_EDIT_TRAFFIC = "ترافیک جدید (گیگابایت) را وارد کنید:"
PLAN_EDIT_PRICE = "قیمت جدید (تومان) را وارد کنید:"
PLAN_EDIT_WHOLESALE_PRICE = "قیمت عمده‌فروشی جدید را وارد کنید (یا '-' برای حذف):"

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

CUSTOMER_SERVICES_HEADER = "سرویس‌های مشتری {telegram_id}:"
CUSTOMER_NO_SERVICES = "این مشتری هیچ سرویسی ندارد."
CUSTOMER_SERVICE_DETAIL = (
    "📦 سرویس #{id}\n"
    "پنل یوزرنیم: {panel_username}\n"
    "وضعیت: {status}\n"
    "مدت: {months} ماه\n"
    "ترافیک: {traffic_gb} گیگ\n"
    "لینک: {link}"
)
CUSTOMER_SERVICE_DISABLED = "سرویس #{id} غیرفعال شد."
CUSTOMER_SERVICE_DELETED = "سرویس #{id} از پنل حذف شد."
CUSTOMER_SERVICE_ADDED = "سرویس با موفقیت برای مشتری اضافه شد.\n🔗 لینک: {link}"
CUSTOMER_WALLET_ADJUSTED = "موجودی کیف پول مشتری از {old} به {new} تومان تغییر یافت."
ASK_WALLET_ADJUST_AMOUNT = "مبلغ را به تومان وارد کنید (مثبت برای افزایش، منفی برای کاهش):"

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
CARD_TOGGLED = "وضعیت کارت تغییر کرد."
NO_CARDS = "هیچ کارتی ثبت نشده است."

ASK_TUNNEL_TARGET = "یوزرنیم/UUID حساب مورد نظر یا 'همه' برای اعمال روی همه حساب‌ها را وارد کنید:"
TUNNEL_ADDED = "تانل با موفقیت اضافه شد."
TUNNEL_REMOVED = "تانل با موفقیت حذف شد."
