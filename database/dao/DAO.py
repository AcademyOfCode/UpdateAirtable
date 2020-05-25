class DAO:
    @staticmethod
    def search(table, field_name, field_value):
        return table.search(field_name, field_value)

    @staticmethod
    def insert(table, fields):
        table.insert(fields)

    @staticmethod
    def get_all(table):
        return table.get_all()