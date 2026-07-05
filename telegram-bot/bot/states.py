from aiogram.fsm.state import State, StatesGroup


class BuyService(StatesGroup):
    user_count = State()
    months = State()
    traffic_gb = State()
    confirm = State()
    awaiting_receipt = State()


class TopUp(StatesGroup):
    amount = State()
    awaiting_receipt = State()


class ManageService(StatesGroup):
    search = State()


class ConnectGuide(StatesGroup):
    platform = State()
    app = State()


class AdminPricing(StatesGroup):
    base_price = State()
    price_per_user = State()
    price_per_month = State()
    price_per_gb = State()


class AdminCustomerLookup(StatesGroup):
    query = State()


class AdminWalletOverride(StatesGroup):
    target = State()
    new_balance = State()
    confirm = State()


class AdminBroadcast(StatesGroup):
    text = State()


class AdminDirectMessage(StatesGroup):
    target = State()
    text = State()


class AdminCards(StatesGroup):
    add_number = State()
    add_holder = State()


class AdminTunnel(StatesGroup):
    target = State()
