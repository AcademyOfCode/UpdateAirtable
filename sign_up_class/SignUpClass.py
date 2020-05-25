class SignUpClass:
    def __init__(self, order_builder):
        self.__time = order_builder.get_class_time()
        self.__day = order_builder.get_class_day()
        self.__venue = order_builder.get_class_venue()
        self.__group = order_builder.get_class_group()
        self.__term = order_builder.get_class_term()

    def get_time(self):
        return self.__time

    def get_day(self):
        return self.__day

    def get_venue(self):
        return self.__venue

    def get_group(self):
        return self.__group

    def get_term(self):
        return self.__term