import os
import asyncio
import logging

from telethon import TelegramClient, types
from telethon.tl.functions.channels import JoinChannelRequest, LeaveChannelRequest
from telethon.errors.rpcerrorlist import UserAlreadyParticipantError, UserNotParticipantError

from alchemysession import AlchemySessionContainer
from asyncpg.exceptions import UniqueViolationError

from res.databaser import Postgres
import config

logging.basicConfig(
    format='%(asctime)s %(levelname)s: %(message)s', datefmt='%d-%m-%y %H:%M:%S',
    filename=config.LOG_FILE, filemode='a'
)

container = AlchemySessionContainer(config.db_URL)
session = container.new_session('1')

DB = Postgres(dsn=config.db_URL)

stuff_lock = asyncio.Lock()
client = TelegramClient(session, config.API_ID, config.API_HASH, device_model='Calculator')
config.MainChannel.ID = None


def post_photo_filter(event):
    post: types.Message = event.message

    params = (post.message, post.post_author, post.grouped_id, post.fwd_from)

    allows = config.AllowPhotoPosts.__dict__.copy()

    if not allows.get('_list'):
        _vars = filter(lambda k: k if not k.startswith('_') else False, allows)
        allows = [allows[item] for item in _vars]
        config.AllowPhotoPosts._list = allows
    else:
        allows = config.AllowPhotoPosts._list

    if event.is_channel and post.to_id.channel_id != config.MainChannel.ID and \
            isinstance(post.media, types.MessageMediaPhoto):

        for i in range(len(params)):
            if params[i]:
                if not allows[i]:
                    return False

        return True

    return False


class CommandResults:
    def __init__(self, text: str = '', file=None, parse_mode=None):
        self.text = text
        self.file = file
        self.parse_mode = parse_mode


class Commands:
    _prefix = '/'

    def help(*args: None) -> CommandResults:
        """Возвращает список доступных комманд"""
        res = CommandResults()

        commands_dict: dict = Commands.__dict__
        for command in commands_dict:
            if not command.startswith('_'):
                description = commands_dict[command].__doc__
                if description:
                    description: str = description.replace('\n', '')
                    desc_splitter = description.split(':param args:')
                    params = '\r'
                    if len(desc_splitter) > 1:
                        params = desc_splitter[1]
                        description = desc_splitter[0]
                    res.text += f'{Commands._prefix}{command} {params} - {description}\n'

        return res

    def status(*args) -> CommandResults:
        """Показывает логи с файла(если настроен)"""

        res = CommandResults()
        show_rows = 15
        arg = args[0] if args else show_rows

        if type(arg) is not int:
            show_rows = int(arg) if int(arg) < show_rows else show_rows

        if config.LOG_FILE:
            with open(config.LOG_FILE, 'r') as logs:
                res.text = "Работаю. Последние логи:\n"
                for i in logs.readlines()[-show_rows:]:
                    res.text += f'`{i}`'
        else:
            res.text = "Все логи находятся в консоли"

        res.parse_mode = 'markdown'
        return res

    def logs(*args: None) -> CommandResults:
        """Возвращает файл с логами"""

        res = CommandResults()
        if config.LOG_FILE:
            res.file = config.LOG_FILE
            res.text = 'Логи'
        else:
            res.text = 'Файл с логами не настроен. Все логи находятся в консоли'

        return res

    def clearlogs(*args: None) -> CommandResults:
        """Очищает логи"""

        res = CommandResults('Логи очищены')
        if config.LOG_FILE:
            with open(config.LOG_FILE, 'w') as logs:
                logs.write('')
                logging.warning('Logs cleared')
        else:
            os.system('cls' if os.name == 'nt' else 'clear')
        return res

    def _curdir(*args: None) -> CommandResults:
        """Просматривает список файлов в текущей директории"""

        res = CommandResults('Все файлы:\n')
        for file in os.listdir(os.curdir):
            res.text += f"`{file}\n`"
        res.parse_mode = 'markdown'
        return res

    async def channels(*args: None) -> CommandResults:
        """Возвращает список отслеживаемых каналов"""
        res = CommandResults(text=f"Список используемых каналов:\n{await DB.show_channels()}")
        return res

    async def config(*args: None) -> CommandResults:
        """Возвращает конфигурацию"""

        res = CommandResults(text=f"`Основная информация:`\n"
                                  f"id канала: {config.MainChannel.ID}\n\n"
                                  f"`Алгоритм проверки картинок:`\n"
                                  f"Количество проверок на дубликат: "
                                  f"{config.algo_limit}\n\n"
                                  f"`База данных:`\n"
                                  f"Количество записей постов в БД: "
                                  f"{await DB.get_count_records_images()}\n")

        res.parse_mode = 'markdown'
        return res

    async def add_channels(*args):
        """Добавляет каналы для приема постов (через пробел)"""

        res = CommandResults()
        for i in args:

            if not i.startswith('@'):
                i = '@' + i

            try:
                await client(JoinChannelRequest(i))

                await DB.add_channel(i)
                res.text += f'Добавлен канал: {i}\n'
                logging.warning(f"Added chat: {i}")
            except UserAlreadyParticipantError:
                res.text += f'Уже подписан на этот канал: {i}\n'
            except UniqueViolationError:
                res.text += f'Уже есть в базе данных этот канал: {i}\n'
        return res

    async def delete_channels(*args):
        """Удаляет отслеживаемые каналы (через пробел)"""

        res = CommandResults()
        for i in args:

            if not i.startswith('@'):
                i = '@' + i

            res.text += f'Удален канал: {i}\n'
            await DB.del_channel(i)
            try:
                await client(LeaveChannelRequest(i))
                logging.warning(f"Deleted chat: {i}")
            except UserNotParticipantError:
                res.text += f'Не подписчик этого канала: {i}\nНо если в базе была запись, она удалена.'

        return res

    async def del_posts(*args) -> CommandResults:
        """Удаляет посты по их id (через пробел)"""

        res = CommandResults("Успешно")
        for post_id_str in args:
            post_id = int(post_id_str)
            await DB.delete_post_by_id(post_id)
            await client.delete_messages("@" + config.MainChannel.USERNAME, message_ids=post_id)
            logging.warning(f'Deleted post: {post_id}')

        return res

    async def send(*args) -> CommandResults:
        """Отправляет сообщение
        :param args:[chat_id||username] [message]"""

        res = CommandResults('Отправлено')
        args = list(args)
        ent = args.pop(0)
        chat_id = int(ent) if ent.isdigit() else ent
        message = ' '.join(args)

        await client.send_message(chat_id, message=message)
        return res
