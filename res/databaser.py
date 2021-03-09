import asyncpg
import config
import ssl


class Postgres(object):

    def __init__(self, dsn: str, ssl: str = 'rds-ca-2019-root.pem'):
        self._dsn = dsn
        self._conn = None
        self._ssl = ssl
        self.ctx = None

    async def connect(self):
        if not self.ctx:
            if self._ssl:
                ctx = ssl.create_default_context(capath=self._ssl)
                ctx.check_hostname = False
                ctx.verify_mode = ssl.CERT_NONE
                self.ctx = ctx

        if isinstance(self._conn, asyncpg.Connection):
            if self._conn.is_closed():
                self._conn = await asyncpg.connect(dsn=self._dsn, ssl=self.ctx)
            return self._conn

        self._conn = await asyncpg.connect(dsn=self._dsn, ssl=self.ctx)
        await self._conn.execute("""CREATE TABLE IF NOT EXISTS imagedata (
        hash text,
        post_id int NOT NULL UNIQUE,
        date timestamp WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS channels (name text NOT NULL UNIQUE)""")
        return self._conn

    async def exe_command(self, command: str):
        conn = await self.connect()
        if command[:6].lower() == 'select':
            show = await conn.fetch(command)
            return show
        else:
            return await conn.execute(f"{command}")

    async def show_channels(self):
        conn = await self.connect()
        show = await conn.fetch("SELECT * FROM channels")
        text = ""
        for i in show:
            text += i[0] + "\n"
        return text

    async def del_channel(self, ch):
        conn = await self.connect()
        await conn.execute("DELETE FROM channels WHERE name = $1", ch)

    async def add_channel(self, ch):
        conn = await self.connect()
        await conn.execute("INSERT INTO channels(name) VALUES($1)", ch)

    async def get_count_records_images(self):
        conn = await self.connect()
        show = await conn.fetchrow(f"SELECT count(imagedata) FROM imagedata")
        return show[0]

    async def get_hash_data(self, lim: int = config.algo_limit):
        conn = await self.connect()
        show = await conn.fetch(f"SELECT hash, post_id, date FROM imagedata ORDER BY post_id DESC LIMIT {lim}")
        return show

    async def add_image(self, hash8, post_id):

        conn = await self.connect()
        await conn.execute("INSERT INTO imagedata(hash, post_id) VALUES($1, $2)", hash8, post_id)

    async def delete_post_by_id(self, post_id):
        conn = await self.connect()
        await conn.execute(
            f'DELETE FROM imagedata WHERE post_id = $1', post_id
        )

    async def delete_last_images(self, lim: int):
        conn = await self.connect()
        await conn.execute(
            f'DELETE FROM imagedata WHERE post_id IN (SELECT post_id FROM imagedata ORDER BY post_id ASC LIMIT {lim})'
        )

    async def close_connect(self):
        conn = await self.connect()
        if not await conn.is_closed():
            await conn.close()

    async def _test(self):
        conn = await self.connect()
        await conn.execute("""ALTER TABLE imagedata DROP COLUMN hash8, DROP COLUMN hash12, DROP COLUMN hash10;""")


if __name__ == '__main__':
    import asyncio
    PG = Postgres(config.db_URL)
    asyncio.get_event_loop().run_until_complete(PG._test())
