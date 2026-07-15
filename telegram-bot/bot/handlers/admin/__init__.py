from aiogram import Router

from . import broadcast, cards, customers, direct_message, orders, plans, test_mgmt, tunnel, wallet_override, wholesalers

router = Router(name="admin")
router.include_router(test_mgmt.router)
router.include_router(orders.router)
router.include_router(plans.router)
router.include_router(customers.router)
router.include_router(wallet_override.router)
router.include_router(broadcast.router)
router.include_router(direct_message.router)
router.include_router(cards.router)
router.include_router(tunnel.router)
router.include_router(wholesalers.router)
