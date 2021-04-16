import os
from TelegramBot.Core.BotCore import BotCore
from TelegramBot.Core.Monitoring import ClearingThread
from TelegramBot.Core.Monitoring import UserNotifyingThread


TOKEN = os.getenv('BOT_TOKEN')


if __name__ == '__main__':
    # ClearingThread(TOKEN).start()
    # UserNotifyingThread(TOKEN).start()
    BotCore(TOKEN).start()
