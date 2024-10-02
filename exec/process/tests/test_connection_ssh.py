import pytest
from greyhorse_process.ssh import AsyncSshConnection


@pytest.mark.asyncio
async def test_async_ssh_run(ssh_host, ssh_username, ssh_root_password) -> None:
    conn = AsyncSshConnection(ssh_host, username=ssh_username, sudo_password=ssh_root_password)

    async with conn.session() as session:
        res = await session.run('echo "123"', shell=True, as_bytes=True)
        assert res.stdout == b'123\n'

        res = await session.run('echo "123"', shell=True)
        assert res.stdout == '123'

        res = await session.run('pwd', shell=False)
        assert res.stdout == '/root'

        res = await session.sudo('whoami', shell=True)
        assert res.stdout == 'root'


@pytest.mark.asyncio
async def test_async_ssh_interactive(ssh_host, ssh_username) -> None:
    conn = AsyncSshConnection(ssh_host, username=ssh_username)

    async with conn.session() as session:
        async with session.create_process('/root/echo.sh', as_bytes=True) as proc:
            line1 = await proc.read_line()
            await proc.write_line(b'123')
            line2 = await proc.read_line()
            await proc.write_line(b'456')
            line3 = await proc.read_line()

        assert line1 == b'hello'
        assert line2 == b'hello 123'
        assert line3 == b'bye 456'

        async with session.create_process('/root/echo.sh') as proc:
            line1 = await proc.read_line()
            await proc.write_line('123')
            line2 = await proc.read_line()
            await proc.write_line('456')
            line3 = await proc.read_line()

        assert line1 == 'hello'
        assert line2 == 'hello 123'
        assert line3 == 'bye 456'
