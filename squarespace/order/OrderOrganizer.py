import copy

class OrderOrganizer:
    def __init__(self, orders):
        self.__orders = orders

    def organize(self):
        organized_orders = []

        for order in self.__orders:
            line_item_number = 0
            for line_item in order['lineItems']:
                order_copy = copy.deepcopy(order)
                line_item_copy = copy.deepcopy(order_copy['lineItems'])

                if (len(line_item['customizations'][0]['value'].split()) > 1 and len(
                        line_item['customizations'][1]['value'].split()) > 1 and len(
                    line_item['customizations'][2]['value'].split()) == 0 and line_item['quantity'] == 2) or \
                        (len(line_item['customizations'][0]['value'].split()) > 1 and len(
                            line_item['customizations'][1]['value'].split()) == 0 and len(
                            line_item['customizations'][2]['value'].split()) > 1 and line_item['quantity'] == 2):
                    organized_orders.append(order_copy)
                elif len(line_item['customizations'][0]['value'].split()) > 1 and len(
                        line_item['customizations'][1]['value'].split()) > 1 and len(
                    line_item['customizations'][2]['value'].split()) > 1 and line_item['quantity'] == 3:
                    organized_orders.append(order_copy)
                    organized_orders.append(order_copy)

                if type(line_item_copy) is list:
                    order_copy['lineItems'] = line_item_copy[line_item_number]
                else:
                    order_copy['lineItems'] = line_item_copy
                organized_orders.append(order_copy)
                line_item_number += 1

        return organized_orders