class StudentContact:
    def __init__(self, order_builder):
        self.__first_name = order_builder.get_contact_first_name()
        self.__second_name = order_builder.get_contact_second_name()
        self.__phone_number = order_builder.get_contact_phone_number()
        self.__email = order_builder.get_contact_email()

    def get_first_name(self):
        return self.__first_name

    def get_second_name(self):
        return self.__second_name

    def get_phone_number(self):
        return self.__phone_number

    def get_email(self):
        return self.__email