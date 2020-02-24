import slack

class Slack:
    def __init__(self, apiKey):
        self.__client = slack.WebClient(token=apiKey)

    def sendMessage(self, channel, message):
        print("Sending slack message in " + channel + ": " + message)

        return self.__client.chat_postMessage(channel=channel, text=message)