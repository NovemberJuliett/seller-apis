## seller.py


Этот скрипт обновляет информацию о товарах и ценах продавца на сайте Ozon.ru.
Для запуска скрипта нужны токен продавца и ID клиента. 

## market.py

Этот скрипт обновляет информацию о товарах и ценах продавца на сайте Яндекс.Маркет,
исходя из логики формирования цен при работе по модели DBS (продавец хранит и продает товар 
самостоятельно, маркетплейс используется как витрина)
и FBS (товар хранится у продавца, но реализует его
маркетплейс). Для запуска скрипта нужны токены продавца, полученные в API Яндекс.Маркета.
