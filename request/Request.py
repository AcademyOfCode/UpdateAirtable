import requests

from request import RequestLimit

class Request:
    def __init__(self, api_url, value=1, period=1, headers=None, params=None):
        self.__api_url = api_url
        self.__value = value
        self.__period = period
        self.__headers = headers
        self.__params = params

    def get_request(self):
        request_limit = RequestLimit.RequestLimit(self.__value, self.__period)

        try:
            with request_limit, requests.get(self.__api_url, headers=self.__headers, params=self.__params) as response:
                return response.json(), None
        except Exception as e:
            print(e)
            return None, e