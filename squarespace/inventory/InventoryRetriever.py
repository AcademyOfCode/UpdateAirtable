from request.Request import Request

from builtins import any

INVENTORY_API_URL = 'https://api.squarespace.com/1.0/commerce/inventory'

class InventoryRetriever:
    def __init__(self, inventory_api_key, request_value=1, request_period=1):
        self.__headers = {
            'Authorization': 'Bearer ' + inventory_api_key,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'
        }
        self.__request_value = request_value
        self.__request_period = request_period

    def get_inventory(self):
        page_number = 1
        inventory = []

        request = Request.Request(INVENTORY_API_URL, self.__request_value, self.__request_period, self.__headers)
        response, error = request.get_request()

        for index in range(len(response['inventory'])):
            inventory.append(response['inventory'][index])

        print('Page ' + str(page_number) + ' Inventory Request Completed.')

        while response['pagination']['hasNextPage'] == True:
            page_number += 1

            params = [
                ('cursor', response['pagination']['nextPageCursor'])
            ]

            request = Request.Request(INVENTORY_API_URL, self.__request_value, params, self.__request_period, self.__headers)
            response, error = request.get_request()

            for index in range(len(response['inventory'])):
                inventory.append(response['inventory'][index])

            print('Page ' + str(page_number) + ' Inventory Request Completed.')

        return self.__filter_inventory(inventory)

    def __filter_inventory(self, inventory):
        filtered_inventory = []

        for i in range(len(inventory)):
            if ('Spring' in inventory[i]['descriptor'].split('[')[0] or 'Summer' in
                inventory[i]['descriptor'].split('[')[0]) and (
                    '\'20' in inventory[i]['descriptor'].split('[')[0] or '2020' in
                    inventory[i]['descriptor'].split('[')[0]):
                current_term_variant = inventory[i]['descriptor']

                if '\'20' in current_term_variant:
                    current_term_variant = current_term_variant.replace('\'20', '2020')

                if ', ' in current_term_variant.split('- ')[1].split('[')[0]:
                    current_term_variant = current_term_variant[0:current_term_variant.index(',')] + ' ' + current_term_variant[
                                                                                                           current_term_variant.index(
                                                                                                         '['):len(
                                                                                                               current_term_variant)]

                if len(current_term_variant.split(',')) > 3:
                    if not any(current_term_variant[0:current_term_variant.rfind(',')] in x for x in filtered_inventory):
                        filtered_inventory.append(current_term_variant)
                else:
                    if not any(current_term_variant in x for x in filtered_inventory):
                        filtered_inventory.append(current_term_variant)

        return self.__split_inventory(filtered_inventory)

    def __split_inventory(self, inventory):
        grouped = {}
        for item in inventory:
            key = item.split(' [')[0]
            grouped.setdefault(key, []).append(item)

        return list(grouped.values())