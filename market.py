import datetime
import logging.config
from environs import Env
from seller import download_stock

import requests

from seller import divide, price_conversion

logger = logging.getLogger(__file__)


def get_product_list(page, campaign_id, access_token):
    """Выводит список товаров в каталоге с параметрами каждого товара

    Аргументы:
        page: идентификатор страницы c результатами
        campaign_id: идентификатор кампании в API и магазина в кабинете
        access_token: ключ авторизации в кабинете

    Возвращает:
        результат запроса в формате json

    Пример корректного выполнения функции:
            {
            "offerIds": [
                "124234"
            ],
            "cardStatuses": [
                "HAS_CARD_CAN_NOT_UPDATE"
            ],
            "categoryIds": [
                343
            ],
            "vendorNames": [
                "STR"
            ],
            "tags": [
                "str_product"
            ],
            "archived": false
        }
    Пример некорректного выполнения функции:
        {"errors": [
            {
                "code":"UNAUTHORIZED",
                "message":"OAuth credentials are not specified"
            }
        ],
        "status":"ERROR"}
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {
        "page_token": page,
        "limit": 200,
    }
    url = endpoint_url + f"campaigns/{campaign_id}/offer-mapping-entries"
    response = requests.get(url, headers=headers, params=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def update_stocks(stocks, campaign_id, access_token):
    """Передает данные об остатках товаров на витрине.

    Аргументы:
        stocks: данные об остатках товаров
        campaign_id: идентификатор кампании в API и магазина в кабинете
        access_token: ключ авторизации в кабинете

    Возвращает:
        результат запроса в формате json

    Пример корректного выполнения функции:

            {
            "skus": [
                {
                    "sku": "234234",
                    "warehouseId": 343,
                    "items": [
                        {
                            "count": 1,
                            "type": "FIT",
                            "updatedAt": "2022-12-29T18:02:01Z"
                        }
                    ]
                }
            ]
        }

     Пример некорректного выполнения функции:
        {"errors": [
            {
                "code":"UNAUTHORIZED",
                "message":"OAuth credentials are not specified"
            }
        ],
        "status":"ERROR"}
 """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"skus": stocks}
    url = endpoint_url + f"campaigns/{campaign_id}/offers/stocks"
    response = requests.put(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def update_price(prices, campaign_id, access_token):
    """Устанавливает цены на товары в магазине

    Аргументы:
        prices: список товаров
        campaign_id: идентификатор кампании в API и магазина в кабинете
        access_token: ключ авторизации в кабинете

    Возвращает:
        результат запроса в формате json

    Пример корректного выполнения функции:
        {
        "offers": [
            {
                "offerId": "3456",
                "id": "34",
                "feed": {
                    "id": 45
                },
                "price": {
                    "value": 345,
                    "discountBase": 45,
                    "currencyId": "RUR",
                    "vat": 0
                },
                "marketSku": 34,
                "shopSku": "1234"
            }
        ]
    }

    Пример некорректного выполнения функции:
        {"errors": [
            {
                "code":"UNAUTHORIZED",
                "message":"OAuth credentials are not specified"
            }
        ],
        "status":"ERROR"}
    """
    endpoint_url = "https://api.partner.market.yandex.ru/"
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json",
        "Host": "api.partner.market.yandex.ru",
    }
    payload = {"offers": prices}
    url = endpoint_url + f"campaigns/{campaign_id}/offer-prices/updates"
    response = requests.post(url, headers=headers, json=payload)
    response.raise_for_status()
    response_object = response.json()
    return response_object


def get_offer_ids(campaign_id, market_token):
    """Выводит артикулы товаров магазина на Яндекс маркете

    Аргументы:
        campaign_id: идентификатор кампании в API и магазина в кабинете
        market_token: учетные данные владельца магазина

    Возвращает:
        список артикулов товаров

    Пример корректного выполнения функции:
        offer_ids = ["12345б", "873987", "8987987"]

    Пример некорректного выполнения функции:
        offer_ids = []
    """
    page = ""
    product_list = []
    while True:
        some_prod = get_product_list(page, campaign_id, market_token)
        product_list.extend(some_prod.get("offerMappingEntries"))
        page = some_prod.get("paging").get("nextPageToken")
        if not page:
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer").get("shopSku"))
    return offer_ids


def create_stocks(watch_remnants, offer_ids, warehouse_id):
    """Обновляет список товаров магазина

    Аргументы:
        watch_remnants: остатки часов
        offer_ids: артикулы товаров
        warehouse_id: идентификатор склада

    Возвращает:
        обновленный список товаров после сверки остатков часов с наличием товаров
        магазина на Яндекс Маркете

    Пример корректного выполнения функции:

    [
    {
        "sku": "123",
        "warehouseId": "W123",
        "items": [
            {
                "count": 5,
                "type": "FIT",
                "updatedAt": "2023-11-25T12:30:45Z",
            }
        ],
    }
    ]

    Пример некорректного выполнения функции:
    []
    """
    # Уберем то, что не загружено в market
    stocks = list()
    date = str(datetime.datetime.utcnow().replace(microsecond=0).isoformat() + "Z")
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append(
                {
                    "sku": str(watch.get("Код")),
                    "warehouseId": warehouse_id,
                    "items": [
                        {
                            "count": stock,
                            "type": "FIT",
                            "updatedAt": date,
                        }
                    ],
                }
            )
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append(
            {
                "sku": offer_id,
                "warehouseId": warehouse_id,
                "items": [
                    {
                        "count": 0,
                        "type": "FIT",
                        "updatedAt": date,
                    }
                ],
            }
        )
    return stocks


def create_prices(watch_remnants, offer_ids):
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "id": str(watch.get("Код")),
                # "feed": {"id": 0},
                "price": {
                    "value": int(price_conversion(watch.get("Цена"))),
                    # "discountBase": 0,
                    "currencyId": "RUR",
                    # "vat": 0,
                },
                # "marketSku": 0,
                # "shopSku": "string",
            }
            prices.append(price)
    return prices


async def upload_prices(watch_remnants, campaign_id, market_token):
    offer_ids = get_offer_ids(campaign_id, market_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_prices in list(divide(prices, 500)):
        update_price(some_prices, campaign_id, market_token)
    return prices


async def upload_stocks(watch_remnants, campaign_id, market_token, warehouse_id):
    offer_ids = get_offer_ids(campaign_id, market_token)
    stocks = create_stocks(watch_remnants, offer_ids, warehouse_id)
    for some_stock in list(divide(stocks, 2000)):
        update_stocks(some_stock, campaign_id, market_token)
    not_empty = list(
        filter(lambda stock: (stock.get("items")[0].get("count") != 0), stocks)
    )
    return not_empty, stocks


def main():
    env = Env()
    market_token = env.str("MARKET_TOKEN")
    campaign_fbs_id = env.str("FBS_ID")
    campaign_dbs_id = env.str("DBS_ID")
    warehouse_fbs_id = env.str("WAREHOUSE_FBS_ID")
    warehouse_dbs_id = env.str("WAREHOUSE_DBS_ID")

    watch_remnants = download_stock()
    try:
        # FBS
        offer_ids = get_offer_ids(campaign_fbs_id, market_token)
        # Обновить остатки FBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_fbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_fbs_id, market_token)
        # Поменять цены FBS
        upload_prices(watch_remnants, campaign_fbs_id, market_token)

        # DBS
        offer_ids = get_offer_ids(campaign_dbs_id, market_token)
        # Обновить остатки DBS
        stocks = create_stocks(watch_remnants, offer_ids, warehouse_dbs_id)
        for some_stock in list(divide(stocks, 2000)):
            update_stocks(some_stock, campaign_dbs_id, market_token)
        # Поменять цены DBS
        upload_prices(watch_remnants, campaign_dbs_id, market_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
