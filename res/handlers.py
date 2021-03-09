from telethon import events
from telethon.tl.custom.message import Message

from res import algo
from res.pkg import *


@client.on(events.NewMessage(incoming=True, func=post_photo_filter))
async def posts_handler(event):
    post = event.message

    from_channel = await event.get_sender()
    reference = 'splash.jpg'
    async with stuff_lock:
        if os.path.exists(reference):
            os.remove(reference)

        await client.download_media(message=event.message, file=reference.split('.')[0])
        image_hash = algo.calc_im_hash(reference, bit=8)

        hash_data = await DB.get_hash_data(config.algo_limit)
        if hash_data:
            for b_hash in hash_data:
                diff = algo.compare_hash(image_hash, b_hash[0])
                if diff <= 1:
                    await client.send_message(config.admins[0],
                                              message=f'Повтор выше от https://t.me/{from_channel.username}/{post.id}\n'
                                                      f'Наш от https://t.me/{config.MainChannel.USERNAME}/'
                                                      f'{b_hash[1]}\n'
                                                      f'Результат: {diff}', file=post)

                    os.remove(reference)
                    logging.warning(f'Repeat: https://t.me/{config.MainChannel.USERNAME}/{b_hash[1]} '
                                    f'and https://t.me/{from_channel.username}/{post.id}  Diff: {diff}')
                    return

        posted = await client.send_message("@" + config.MainChannel.USERNAME, file=post, )
        await DB.add_image(image_hash, posted.id)
        logging.warning(f'Posted pic as {posted.id} from: https://t.me/{from_channel.username}/{post.id}')


@client.on(events.NewMessage(incoming=True))
async def debug_income_handler(event):
    pass


@client.on(events.NewMessage(chats=config.admins, func=lambda e: e.message.message.startswith(Commands._prefix)))
async def commands_handler(event):
    msg: Message = event.message
    arguments = msg.message.split(' ')
    command = arguments.pop(0)[1:]
    get_command = Commands.__dict__.get(command)

    if get_command:
        if asyncio.iscoroutinefunction(get_command):
            result: CommandResults = await get_command(*arguments)
        else:
            result: CommandResults = get_command(*arguments)

        await client.send_message(msg.from_id,
                                  message=result.text,
                                  file=result.file,
                                  parse_mode=result.parse_mode)
    else:
        await event.reply('Неизвестная команда')

    raise events.StopPropagation


@client.on(events.NewMessage(incoming=True, func=lambda e: e.is_private))
async def message_handler(event):
    msg: Message = event.message
    who = await event.get_sender()

    if msg.reply_to_msg_id and msg.from_id in config.admins:
        mes: Message = await client.get_messages(msg.from_id, ids=msg.reply_to_msg_id)
        try:
            chat_id = int(mes.text.split('<ID>', 2)[1])
            await client.send_message(chat_id, msg.text)
        except IndexError:
            pass

        return

    message_contain = f"Сообщение от `{who.first_name}`, <ID>{who.id}<ID>\n\n{msg.text}"
    if msg.text or msg.file:
        for admin in config.admins:
            if type(admin) == int:
                await client.send_message(admin, message_contain, file=msg.file)
