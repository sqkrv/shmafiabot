from shmafiabot import ShmafiaBot
import os

if __name__ == '__main__':
    shmafiabot = ShmafiaBot(os.getenv('BOT_NAME'), os.getenv('API_ID'), os.getenv('API_HASH'), bot_token=os.getenv('BOT_TOKEN'))
    shmafiabot.run()
