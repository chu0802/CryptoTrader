import logging

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

SLACK_DEFAULT_CUSTOM_ARG = {
    "slack_emoji": ":shiba-head:",
    "emoji_repeat_time": 3,
    "set_prefix": True,
    "set_postfix": False,
}


class SlackBot:
    def __init__(self, api_token, channel_id):
        self.client = WebClient(token=api_token)
        self.channel_id = channel_id

    def set_customize_message(
        self,
        message,
        slack_emoji=None,
        emoji_repeat_time=3,
        set_prefix=False,
        set_postfix=False,
    ):
        if not slack_emoji:
            slack_emoji = []
        if not isinstance(slack_emoji, list):
            slack_emoji = [slack_emoji]

        slack_emoji *= emoji_repeat_time

        total_messages = (
            (slack_emoji if set_prefix else [])
            + [message]
            + (slack_emoji if set_postfix else [])
        )

        return " ".join(total_messages)

    def send_one_message(self, message):
        try:
            _ = self.client.chat_postMessage(
                channel=self.channel_id,
                text=message,
            )
        except SlackApiError as e:
            logging.error(f"Error: {e}")

    def send_messages(self, message_dict, **slack_customize_arguments):
        for k, v in message_dict.items():
            message = f"*{k}*: {v}"
            if len(slack_customize_arguments) > 0:
                message = self.set_customize_message(
                    message, **slack_customize_arguments
                )
            self.send_one_message(message)
