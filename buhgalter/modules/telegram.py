from telegram import Bot
from telegram.error import TelegramError


class TgBot():
    def __init__(self, token, chat_id):
        self.bot = Bot(token=token)
        self.chat_id = chat_id

    async def send_image(self, image_path):
        try:
            with open(image_path, 'rb') as image_file:
                await self.bot.send_photo(chat_id=self.chat_id, photo=image_file)
            print("Image successfully sent.")
        except TelegramError as e:
            print(f"Failed to send image: {e}")

    async def seng_message(self, message):
        try:
            await self.bot.send_message(chat_id=self.chat_id, text=message)
            print("Message successfully sent.")
        except TelegramError as e:
            print(f"Failed to send message: {e}")
