from aiogram.fsm.state import State, StatesGroup


class BuyService(StatesGroup):
    choosing_plan = State()
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


class AdminCustomerLookup(StatesGroup):
    query = State()
    manage = State()
    add_service_plan = State()
    adjust_wallet_amount = State()


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


class AdminPlans(StatesGroup):
    add_name = State()
    add_user_count = State()
    add_months = State()
    add_traffic_gb = State()
    add_price = State()
    add_wholesale_price = State()
    edit_field = State()
    edit_value = State()


class AdminWholesalers(StatesGroup):
    add_wholesaler = State()
    remove_wholesaler = State()


class AdminTunnel(StatesGroup):
    target = State()
