import io
import logging.config
import os
import re
import zipfile
from environs import Env

import pandas as pd
import requests

logger = logging.getLogger(__file__)


def get_product_list(last_id, client_id, seller_token):
    """Выводит список товаров магазина на Озоне

    Аргументы:
        last_id: идентификатор последнего значения на странице
        client_id: идентификатор клиента
        seller_token: API клиента

    Возвращает:
        результат запроса в формате json

    Пример корректного выполнения функции:
        {
          "result": {
            "items": [
              {
                "product_id": 223681945,
                "offer_id": "136748"
              }
            ],
            "total": 1,
            "last_id": "bnVсbA=="
          }
        }

    Пример некорректного выполнения функции:
        {
            "code":16,
            "message":"Client-Id and Api-Key headers are required"
        }
    """

    url = "https://api-seller.ozon.ru/v2/product/list"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {
        "filter": {
            "visibility": "ALL",
        },
        "last_id": last_id,
        "limit": 1000,
    }
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    response_object = response.json()
    return response_object.get("result")


def get_offer_ids(client_id, seller_token):
    """Выводит артикулы товаров магазина на Озоне

    Аргументы:
        client_id: идентификатор клиента
        seller_token: API клиента

    Возвращает:
       список артикулов товаров

    Пример корректного выполнения функции:
        offer_ids = ["12345б", "873987", "8987987"]

    Пример некорректного выполнения функции:
        offer_ids = []
    """
    last_id = ""
    product_list = []
    while True:
        some_prod = get_product_list(last_id, client_id, seller_token)
        product_list.extend(some_prod.get("items"))
        total = some_prod.get("total")
        last_id = some_prod.get("last_id")
        if total == len(product_list):
            break
    offer_ids = []
    for product in product_list:
        offer_ids.append(product.get("offer_id"))
    return offer_ids


def update_price(prices: list, client_id, seller_token):
    """Позволяет изменить цену одного или нескольких товаров.

    Аргументы:
        prices: список цен на товары
        client_id: идентификатор клиента
        seller_token: API клиента

    Возвращает:
        результат запроса в формате json

    Пример корректного выполнения функции:
        {
          "result": [
            {
              "product_id": 1386,
              "offer_id": "PH8865",
              "updated": true,
              "errors": []
            }
          ]
        }

    Пример некорректного выполнения функции:
        {
            "code":16,
            "message":"Client-Id and Api-Key headers are required"
        }
    """
    url = "https://api-seller.ozon.ru/v1/product/import/prices"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"prices": prices}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def update_stocks(stocks: list, client_id, seller_token):
    """Обновляет информацию о количестве товара в наличии

     Аргументы:
        stocks: список товаров на складах
        client_id: идентификатор клиента
        seller_token: API клиента

    Возвращает:
        результат запроса в формате json

    Пример корректного выполнения функции:
        {
            "result": [
                {
                "product_id": 55946,
                "offer_id": "PG-2404С1",
                "updated": true,
                "errors": []
                }
            ]
        }
    Пример некорректного выполнения функции:
        {
            "code":16,
            "message":"Client-Id and Api-Key headers are required"
        }
    """
    url = "https://api-seller.ozon.ru/v1/product/import/stocks"
    headers = {
        "Client-Id": client_id,
        "Api-Key": seller_token,
    }
    payload = {"stocks": stocks}
    response = requests.post(url, json=payload, headers=headers)
    response.raise_for_status()
    return response.json()


def download_stock():
    """Скачивает архив с файлом "ostatki" с сайта магазина часов

    Возвращает:
        список словарей с информацией об остатках часов

    Пример корректного выполнения функции:
        [{'Код': '', 'Наименование товара': 'BURETT',
        'Изображение': '', 'Цена': '', 'Количество': '','Заказ': ''},
        {'Код': 46864, 'Наименование товара': 'Дисплей BURETT', 'Изображение': 'Показать', 'Цена': "3'000.00 руб.",
        'Количество': 4, 'Заказ': ''}]

    Пример некорректного выполнения функции:
        []
    """
    casio_url = "https://timeworld.ru/upload/files/ostatki.zip"
    session = requests.Session()
    response = session.get(casio_url)
    response.raise_for_status()
    with response, zipfile.ZipFile(io.BytesIO(response.content)) as archive:
        archive.extractall(".")
    excel_file = "ostatki.xls"
    watch_remnants = pd.read_excel(
        io=excel_file,
        na_values=None,
        keep_default_na=False,
        header=17,
    ).to_dict(orient="records")
    os.remove("./ostatki.xls")
    return watch_remnants


def create_stocks(watch_remnants, offer_ids):
    """Обновляет список товаров магазина на Озоне

    Аргументы:
        watch_remnants: остатки часов
        offer_ids: артикулы товаров магазина на Озоне

    Возвращает:
        обновленный список товаров после сверки остатков часов с наличием товаров
        магазина на Озоне

    Пример корректного выполнения функции:
        stocks = ["offer_id": offer_id, "stock": 0]

    Пример некорректного выполнения функции:
        []
    """
    # Уберем то, что не загружено в seller
    stocks = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            count = str(watch.get("Количество"))
            if count == ">10":
                stock = 100
            elif count == "1":
                stock = 0
            else:
                stock = int(watch.get("Количество"))
            stocks.append({"offer_id": str(watch.get("Код")), "stock": stock})
            offer_ids.remove(str(watch.get("Код")))
    # Добавим недостающее из загруженного:
    for offer_id in offer_ids:
        stocks.append({"offer_id": offer_id, "stock": 0})
    return stocks


def create_prices(watch_remnants, offer_ids):
    """Создает цены в обновленном списке товаров магазина на Озоне

    Аргументы:
        watch_remnants: остатки часов
        offer_ids: артикулы товаров магазина на Озоне

    Возвращает:
        список словарей с ценами на товары

    Пример корректного выполнения функции:
        price = [{
                "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": 3453465,
                "old_price": "0",
                "price": 5990,
            }]

    Пример некорректного выполнения функции:
        price = []
    """
    prices = []
    for watch in watch_remnants:
        if str(watch.get("Код")) in offer_ids:
            price = {
                "auto_action_enabled": "UNKNOWN",
                "currency_code": "RUB",
                "offer_id": str(watch.get("Код")),
                "old_price": "0",
                "price": price_conversion(watch.get("Цена")),
            }
            prices.append(price)
    return prices


def price_conversion(price: str) -> str:
    """Преобразует цену товара к целочисленному формату.

    Аргументы:
        price (str): строка с ценой товара

    Возвращает:
        str: строка, содержащая только цифры

    Пример корректного исполнения функции:
    >>> "5'990.00 руб."
    >>> 5990
    Пример некорректного исполнения функции:
    >>> "5'990 00"
    >>> 599000
    """
    return re.sub("[^0-9]", "", price.split(".")[0])


def divide(lst: list, n: int):
    """Делит список lst на части по n элементов

    Аргументы:
         lst: list: исходный список чисел
         n: int: сколько элементов будет в каждой части списка после раздела

    Возвращает:
        список со списками по n элементов в каждом

    Пример корректного исполнения функции:
    list = [[1, 2, 3], [4, 5, 6], [7, 8, 9]]

    Пример некорректного исполнения функции:
    list = [1, 2, 3, 4, 5, 6]
    """
    for i in range(0, len(lst), n):
        yield lst[i: i + n]


async def upload_prices(watch_remnants, client_id, seller_token):
    """Загружает обновленные цены на товары

    Аргументы:
        watch_remnants: остатки часов
        client_id: идентификатор клиента
        seller_token: API клиента

    Возвращает:
        список цен на товары

     Пример корректного исполнения функции:
        [
            {"offer_id": 1, "price": 5000},
            {"offer_id": 2, "price": 7599},
            {"offer_id": 3, "price": 1205},
        ]

    Пример некорректного исполнения функции:
        [
            {"offer_id": 0, "price": 0}
        ]
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    prices = create_prices(watch_remnants, offer_ids)
    for some_price in list(divide(prices, 1000)):
        update_price(some_price, client_id, seller_token)
    return prices


async def upload_stocks(watch_remnants, client_id, seller_token):
    """Загружает обновленные остатки товаров

    Аргументы:
        watch_remnants: остатки часов
        client_id: идентификатор клиента
        seller_token: API клиента

    Возвращает:
        список товаров, наличие которых не равно 0, и обновленный список остатков товаров

    Пример корректного исполнения функции:
        not_empty = ["offer_id": 245345, "stock": 150]
        stocks = [{"offer_id": 12345, "stock": 1223}, {"offer_id": 1345, "stock": 45} ]

    Пример некорректного исполнения функции:
        not_empty = ["offer_id": 245345, "stock": 0]
        stocks = ["offer_id": 0, "stock": 0]
    """
    offer_ids = get_offer_ids(client_id, seller_token)
    stocks = create_stocks(watch_remnants, offer_ids)
    for some_stock in list(divide(stocks, 100)):
        update_stocks(some_stock, client_id, seller_token)
    not_empty = list(filter(lambda stock: (stock.get("stock") != 0), stocks))
    return not_empty, stocks


def main():
    env = Env()
    seller_token = env.str("SELLER_TOKEN")
    client_id = env.str("CLIENT_ID")
    try:
        offer_ids = get_offer_ids(client_id, seller_token)
        watch_remnants = download_stock()
        # Обновить остатки
        stocks = create_stocks(watch_remnants, offer_ids)
        for some_stock in list(divide(stocks, 100)):
            update_stocks(some_stock, client_id, seller_token)
        # Поменять цены
        prices = create_prices(watch_remnants, offer_ids)
        for some_price in list(divide(prices, 900)):
            update_price(some_price, client_id, seller_token)
    except requests.exceptions.ReadTimeout:
        print("Превышено время ожидания...")
    except requests.exceptions.ConnectionError as error:
        print(error, "Ошибка соединения")
    except Exception as error:
        print(error, "ERROR_2")


if __name__ == "__main__":
    main()
