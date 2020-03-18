from squarespace.inventory.InventoryRetriever import InventoryRetriever
from squarespace.order.OrderRetriever import OrderRetriever

REQUEST_VALUE = 120
REQUEST_PERIOD = 60

class Squarespace:
    def __init__(self, squarespace_order_api_key, squarespace_inventory_api_key):
        self.__pages = []
        self.__squarespace_order_api_key = squarespace_order_api_key
        self.__squarespace_inventory_api_key = squarespace_inventory_api_key

    def get_orders_by_date(self, start_date, end_date):
        order_retriever = OrderRetriever(self.__squarespace_order_api_key, REQUEST_VALUE, REQUEST_PERIOD)
        return order_retriever.get_orders_by_date(start_date, end_date)

    def get_order_by_id(self):
        pass

    def get_inventory(self):
        inventory_retiever = InventoryRetriever(self.__squarespace_inventory_api_key, REQUEST_VALUE, REQUEST_PERIOD)
        return inventory_retiever.get_inventory()