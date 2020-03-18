from order import OrderPage
from request import Request
from squarespace.order import OrderOrganizer

ORDER_API_URL = 'https://api.squarespace.com/1.0/commerce/orders'

class OrderRetriever:
    def __init__(self, order_api_key, request_value=1, request_period=1):
        self.__headers = {
            'Authorization': 'Bearer ' + order_api_key,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
        }
        self.__product_names_to_ignore = ['Custom payment amount']
        self.__request_value = request_value
        self.__request_period = request_period

    def get_orders_by_date(self, start_date, end_date):
        orders = []
        page_number = 1

        params = [
            ('modifiedAfter', start_date),
            ('modifiedBefore', end_date),
            ('fulfillmentStatus', 'PENDING')
        ]

        request = Request.Request(ORDER_API_URL, self.__request_value, self.__request_period, self.__headers, params)
        response, error = request.get_request()

        if not response['result']:
            print("Orders between " + start_date + " and " + end_date + " not found")
            return None

        # orderPages = OrderPages.OrderPages()
        order_page = OrderPage.OrderPage(response['result'], self.__product_names_to_ignore)

        prev_order_id = 0

        for order in order_page.get_page():
            if order['orderNumber'] == prev_order_id and (len(order['lineItems']['customizations'][1]['value'].split()) > 1 or len(order['lineItems']['customizations'][2]['value'].split()) > 1):
                multiple_order_index += 1

                if multiple_order_index >= 3:
                    multiple_order_index = 0
                    print("Error: too many orders from customer")
            else:
                multiple_order_index = 0

            orders.append(order)
            prev_order_id = order['orderNumber']

        print('Page ' + str(page_number) + ' Order Request Completed.')

        while response['pagination']['hasNextPage'] == True:
            page_number += 1

            params = [
                ('cursor', response['pagination']['nextPageCursor'])
            ]

            request = Request.Request(ORDER_API_URL, self.__request_value, self.__request_period, self.__headers, params)
            response, error = request.get_request()

            order_page = OrderPage.OrderPage(response['result'], self.__product_names_to_ignore)

            for order in order_page.get_page():
                if order['orderNumber'] == prev_order_id and (
                        len(order['lineItems']['customizations'][1]['value'].split()) > 1 or len(
                    order['lineItems']['customizations'][2]['value'].split()) > 1):
                    multiple_order_index += 1

                    if multiple_order_index >= 3:
                        multiple_order_index = 0
                        print("Error: too many orders from customer")
                else:
                    multiple_order_index = 0

                orders.append(order)
                prev_order_id = order['orderNumber']

            print('Page ' + str(page_number) + ' Order Request Completed.')

        order_organizer = OrderOrganizer.OrderOrganizer(orders)

        return order_organizer.organize()

    def get_orders_id(self, order_id):
        request = Request.Request(ORDER_API_URL + '/' + order_id, self.__request_value, self.__request_period, self.__headers)
        response, error = request.get_request()

        if not response['result']:
            print("Order ID " + order_id + " not found")
            return None

        print('Exporting Order ' + order_id)

        order_organizer = OrderOrganizer.OrderOrganizer(response['result'])

        return order_organizer.organize()