class OrderPages:
    def __init__(self, response, product_names_to_ignore):
        self.__pages = []
        self.__product_names_to_ignore = product_names_to_ignore
        self.__page = []
        self.__populate(response)

    def __populate(self, response):
        for order in response:
            skipOrder = False
            for productName in self.__product_names_to_ignore:
                if productName in order['lineItems'][0]['productName'] or order['lineItems'][0]['productName'] in productName:
                    skipOrder = True
                    break
            if not skipOrder and order['refundedTotal']['value'] == '0.00':
                self.__page.append(order)

    def get_pages(self):
        return self.__pages