import slack

class Slack:
    def __init__(self, api_key):
        self.__client = slack.WebClient(token=api_key)

    def send_message(self, channel, message):
        print("Sending slack message in " + channel + ": " + message)

        return self.__client.chat_postMessage(channel=channel, text=message)