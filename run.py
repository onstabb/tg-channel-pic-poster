from res.handlers import *

client.start()
logging.warning('Started')

_MAIN_CHANNEL_PEER = client.loop.run_until_complete(client.get_input_entity('@' + config.MainChannel.USERNAME))
config.MainChannel.ID = _MAIN_CHANNEL_PEER.channel_id
client.run_until_disconnected()
