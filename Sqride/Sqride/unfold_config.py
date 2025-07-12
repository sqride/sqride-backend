from django.utils.translation import gettext_lazy as _
from django.templatetags.static import static


UNFOLD = {
    "SITE_TITLE": "Sqride Admin Dashboard",
    "SITE_HEADER": "Sqride Admin Panel",
    "SHOW_HISTORY": True,
    "DARK_MODE": True,
    "SIDEBAR": {
        "show_search": True,
        "show_all_applications": True,
    },
    
    "SITE_DROPDOWN": [
        {
            "icon": "diamond",
            "title": _("SQride"),
            "link": "https://sqride.com",
        },
        
    ],
    "SITE_SYMBOL": "speed",  # symbol from icon set
    "SITE_FAVICONS": [
        {
            "rel": "icon",
            "sizes": "32x32",
            "type": "image/svg+xml",
            "href": lambda request: static("favicon.svg"),
        },
    ],
     "SIDEBAR": {
        "show_search": True,
        "show_all_applications": False,

        "navigation": [
            {
                "title": "Main",
                "separator": True,
                "collapsible": False,
                "items": [
                    {
                        "title": "Dashboard",
                        "icon": "dashboard",
                        "link": "/admin/",
                    },
                ],
            },
            {
                "title": "POS",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Orders",
                        "icon": "receipt_long",
                        "link": "/admin/orders/order/",
                    },
                    {
                        "title": "Order Items",
                        "icon": "shopping_cart",
                        "link": "/admin/orders/orderitem/",
                    },
                ],
            },
            {
                "title": "Food",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": "/admin/items/category/",
                    },
                    {
                        "title": "Items",
                        "icon": "restaurant_menu",
                        "link": "/admin/items/item/",
                    },
                    {
                        "title": "Modifier",
                        "icon": "tune",
                        "link": "/admin/items/modifier/",
                    },
                    {
                        "title": "Ingredients",
                        "icon": "kitchen",
                        "link": "/admin/items/itemingredient/",
                    },
                ],
            },
            {
                "title": "Inventory",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Categories",
                        "icon": "category",
                        "link": "/admin/inventory/inventorycategory/",
                    },
                    {
                        "title": "Inventory Items",
                        "icon": "widgets",
                        "link": "/admin/inventory/inventory/",
                    },
                    {
                        "title": "Transactions",
                        "icon": "compare_arrows",
                        "link": "/admin/inventory/inventorytransaction/",
                    },
                    {
                        "title": "Stock Adjustments",
                        "icon": "tune",
                        "link": "/admin/inventory/stockadjustment/",
                    },
                    {
                        "title": "Suppliers",
                        "icon": "local_shipping",
                        "link": "/admin/inventory/supplier/",
                    },
                ],
            },
            {
                "title": "Settings",
                "separator": True,
                "collapsible": True,
                "items": [
                    {
                        "title": "Branches",
                        "icon": "store",
                        "link": "/admin/restaurants/branch/",
                    },
                    {
                        "title": "Users",
                        "icon": "group",
                        "link": "/admin/accounts/user/",
                    },
                    {
                        "title": "Currencies",
                        "icon": "payments",
                        "link": "/admin/restaurants/currency/",
                    },
                ],
            },
        ],
    },
    

}