class OrderBuilder:
    def __init__(self, orderJsonObject, multipleOrderIndex):
        self.__first_name = orderJsonObject["lineItems"]["customizations"][multipleOrderIndex]["value"].split()[0].title().replace("\"", "")
        self.__second_name = orderJsonObject["lineItems"]["customizations"][multipleOrderIndex]["value"].split()[0].title().replace("\"", "")
        self.__date_of_birth = orderJsonObject["lineItems"]["customizations"][multipleOrderIndex+3]["value"]
        self.__school_and_class = orderJsonObject["lineItems"]["customizations"][6]["value"]
        self.__class_time = orderJsonObject["lineItems"]["variantOptions"][0]["value"].split(", ")[1].replace(" ", "")
        self.__class_day = orderJsonObject["lineItems"]["variantOptions"][0]["value"].split(",")[0]
        self.__class_venue = orderJsonObject["lineItems"]["productName"].split("- ")[1].split(",")[0].replace("'", "")
        self.__class_group = None
        self.__class_term = orderJsonObject["lineItems"]["productName"].split(" -")[0].split(",")[0].replace("\"20", "2020")
        self.__contact_first_name = orderJsonObject["billingAddress"]["firstName"].title()
        self.__contact_second_name = orderJsonObject["billingAddress"]["lastName"].title()
        self.__contact_phone_number = orderJsonObject["billingAddress"]["phone"]
        self.__contact_email = orderJsonObject["customerEmail"]
        if "Yes" in orderJsonObject["lineItems"]["customizations"][7]["value"]:
            self.__returning = "Yes"
        else:
            self.__returning = ""
        if "I DO NOT" in orderJsonObject["lineItems"]["customizations"][11]["value"]:
            self.__photography_consent = "No"
        else:
            self.__photography_consent = "Yes"
        self.__other_details = orderJsonObject["lineItems"]["customizations"][10]["value"]
    
    def get_first_name(self):
        return self.__first_name
    
    def get_second_name(self):
        return self.__second_name
    
    def get_date_of_birth(self):
        return self.__date_of_birth
    
    def get_school_and_class(self):
        return self.__school_and_class
    
    def get_class_time(self):
        return self.__class_time
    
    def get_class_day(self):
        return self.__class_day
    
    def get_class_venue(self):
        return self.__class_venue

    def get_class_group(self):
        return self.__class_group
    
    def get_class_term(self):
        return self.__class_term

    def get_contact_first_name(self):
        return self.__contact_first_name

    def get_contact_second_name(self):
        return self.__contact_second_name

    def get_contact_phone_number(self):
        return self.__contact_phone_number

    def get_contact_email(self):
        return self.__contact_email

    def get_returning(self):
        return self.__returning

    def get_photography_consent(self):
        return self.__photography_consent

    def get_other_details(self):
        return self.__other_details