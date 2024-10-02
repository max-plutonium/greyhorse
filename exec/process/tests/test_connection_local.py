import os

import pytest
from greyhorse_process.local import AsyncLocalConnection


@pytest.mark.asyncio
async def test_async_local_run(local_root_password) -> None:
    conn = AsyncLocalConnection(sudo_password=local_root_password)

    async with conn.session() as session:
        res = await session.run('echo "123"', shell=True, as_bytes=True)
        assert res.stdout == b'123\n'

        res = await session.run('echo "123"', shell=True)
        assert res.stdout == '123'

        res = await session.run('pwd', shell=False)
        assert res.stdout == os.getcwd()

        res = await session.sudo('whoami', shell=True)
        assert res.stdout == 'root'


@pytest.mark.asyncio
async def test_async_local_interactive(local_root_password) -> None:
    conn = AsyncLocalConnection(sudo_password=local_root_password)

    async with conn.session() as session:
        async with session.create_process(
            f'{os.getcwd()}/tests/echo.sh', as_bytes=True
        ) as proc:
            line1 = await proc.read_line()
            await proc.write_line(b'123')
            line2 = await proc.read_line()
            await proc.write_line(b'456')
            line3 = await proc.read_line()

        assert line1 == b'hello'
        assert line2 == b'hello 123'
        assert line3 == b'bye 456'

        async with session.create_process(f'{os.getcwd()}/tests/echo.sh') as proc:
            line1 = await proc.read_line()
            await proc.write_line('123')
            line2 = await proc.read_line()
            await proc.write_line('456')
            line3 = await proc.read_line()

        assert line1 == 'hello'
        assert line2 == 'hello 123'
        assert line3 == 'bye 456'
