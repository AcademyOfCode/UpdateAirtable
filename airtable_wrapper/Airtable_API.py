from airtable import Airtable

class Airtable_API:
    def __init__(self, base_key, table_name, api_key):
        self.__table = Airtable(base_key, table_name, api_key)

    def search(self, field_name, field_value):
        return self.__table.search(field_name, field_value)

    def insert(self, fields):
        self.__table.insert(fields)

    def get_all(self):
        return self.__table.get_all()