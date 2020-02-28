from student.StudentContact import StudentContact
from sign_up_class.SignUpClass import SignUpClass

class Student:
    def __init__(self, order_builder):
        self.__first_name = order_builder.get_first_name()
        self.__second_name = order_builder.get_second_name()
        self.__date_of_birth = order_builder.get_date_of_birth()
        self.__school_and_class = order_builder.get_school_and_class()
        self.__class = SignUpClass(order_builder)
        self.__contact = StudentContact(order_builder)
        self.__returning = order_builder.get_returning()
        self.__photography_consent = order_builder.get_photography_consent()
        self.__other_details = order_builder.get_other_details()

    def get_first_name(self):
        return self.__first_name

    def get_second_name(self):
        return self.__second_name

    def get_date_of_birth(self):
        return self.__date_of_birth

    def get_school_and_class(self):
        return self.__school_and_class

    def get_class(self):
        return self.__class

    def get_contact(self):
        return self.__contact

    def get_returning(self):
        return self.__returning

    def get_photography_consent(self):
        return self.__photography_consent

    def get_other_details(self):
        return self.__other_details