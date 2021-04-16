from TelegramBot.Core.BotCore import BotCore
from TelegramBot.Core.Monitoring import ClearingThread
from TelegramBot.Core.Monitoring import UserNotifyingThread


TOKEN = '1758576197:AAHO1FZXU2mf977JCjPaSh9S_Y3WQdW5h0k'


if __name__ == '__main__':
    # ClearingThread(TOKEN).start()
    # UserNotifyingThread(TOKEN).start()
    BotCore(TOKEN).starting()
