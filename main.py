import os

from dotenv import load_dotenv

if __name__ == '__main__':
    load_dotenv()
    from shmafiabot import ShmafiaBot

    shmafiabot = ShmafiaBot(os.getenv('BOT_NAME'), os.getenv('API_ID'), os.getenv('API_HASH'),
                            bot_token=os.getenv('BOT_TOKEN'))
    shmafiabot.run()
