FIRST_NAME = "First Name"
SECOND_NAME = "Second Name"
DATE_OF_BIRTH = "Date Of Birth"
SCHOOL_CLASS = "School & Class"
TIME = "Time"
DAY = "Day"
VENUE = "Venue"
GROUP = "Group"
TERM = "Term"
CONTACT_FIRST_NAME = "Contact First Name"
CONTACT_SECOND_NAME = "Contact Second Name"
CONTACT_PHONE_NUMBER = "Contact phone Number"
CONTACT_EMAIL = "Contact Email"
RETURNING = "Returning Student"
PHOTOGRAPHY_CONSENT = "Photography Consent"
OTHER_DETAILS = "Other Details"
IS_SUBSCRIPTION = "Subscription"

class OrderBuilder:
    def __init__(self, order_json_object, multiple_order_index):
        self.__order = {}
        self.__first_name = order_json_object["lineItems"]["customizations"][multiple_order_index]["value"].split()[0].title().replace("\"", "")
        self.__second_name = order_json_object["lineItems"]["customizations"][multiple_order_index]["value"].split()[0].title().replace("\"", "")
        self.__date_of_birth = order_json_object["lineItems"]["customizations"][multiple_order_index+3]["value"]
        self.__school_and_class = order_json_object["lineItems"]["customizations"][6]["value"]
        self.__class_time = order_json_object["lineItems"]["variantOptions"][0]["value"].split(", ")[1].replace(" ", "")
        self.__class_day = order_json_object["lineItems"]["variantOptions"][0]["value"].split(",")[0]
        self.__class_venue = order_json_object["lineItems"]["productName"].split("- ")[1].split(",")[0].replace("'", "")
        self.__class_group = None
        self.__class_term = order_json_object["lineItems"]["productName"].split(" -")[0].split(",")[0].replace("\"20", "2020")
        self.__contact_first_name = order_json_object["billingAddress"]["firstName"].title()
        self.__contact_second_name = order_json_object["billingAddress"]["lastName"].title()
        self.__contact_phone_number = order_json_object["billingAddress"]["phone"]
        self.__contact_email = order_json_object["customerEmail"]
        if "Yes" in order_json_object["lineItems"]["customizations"][7]["value"]:
            self.__returning = "Yes"
        else:
            self.__returning = ""
        if "I DO NOT" in order_json_object["lineItems"]["customizations"][11]["value"]:
            self.__photography_consent = "No"
        else:
            self.__photography_consent = "Yes"
        self.__other_details = order_json_object["lineItems"]["customizations"][10]["value"]
        self.__is_subscription = True if "Subscription" in order_json_object["lineItems"]["productName"] else False

    def build(self):
        self.__order[FIRST_NAME] = self.__first_name
        self.__order[SECOND_NAME] = self.__second_name
        self.__order[DATE_OF_BIRTH] = self.__date_of_birth
        self.__order[SCHOOL_CLASS] = self.__school_and_class
        self.__order[TIME] = self.__class_time
        self.__order[DAY] = self.__class_day
        self.__order[VENUE] = self.__class_venue
        self.__order[GROUP] = self.__class_group
        self.__order[TERM] = self.__class_term
        self.__order[CONTACT_FIRST_NAME] = self.__contact_first_name
        self.__order[CONTACT_SECOND_NAME] = self.__contact_second_name
        self.__order[CONTACT_PHONE_NUMBER] = self.__contact_phone_number
        self.__order[CONTACT_EMAIL] = self.__contact_email
        self.__order[RETURNING]= self.__returning
        self.__order[PHOTOGRAPHY_CONSENT] = self.__photography_consent
        self.__order[OTHER_DETAILS] = self.__other_details
        self.__order[IS_SUBSCRIPTION] = self.__is_subscription
        return self.__order

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