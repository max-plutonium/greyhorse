import shlex
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from datetime import timedelta
from typing import override

import asyncssh
from asyncssh import SSHClientConnection, SSHClientConnectionOptions
from greyhorse.logging import logger

from .abc import AsyncConnection, AsyncSession, CompletedProcess
from .adapters import AsyncProcessAdapter


class AsyncSshSession(AsyncSession):
    def __init__(
        self,
        connection: SSHClientConnection,
        server_string: str,
        sudo_password: str | None = None,
    ) -> None:
        self._connection = connection
        self._sudo_password = sudo_password
        self._server_string = server_string

    @property
    def raw_connection(self) -> SSHClientConnection:
        return self._connection

    @override
    @asynccontextmanager
    async def create_process(
        self,
        command: str,
        shell: bool = False,
        sudo: bool = False,
        as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> Callable[..., AbstractAsyncContextManager[AsyncProcessAdapter]]:
        use_terminal = False
        input = input.encode('utf-8') if isinstance(input, str) else input
        command = shlex.split(command, comments=True)

        if sudo:
            if self._sudo_password is None:
                logger.warning('Sudo used without the password')
            use_terminal = True
            command = ['sudo', '-S', *command]

        if shell:
            command = [' '.join(command)]

        async with self._connection.create_process(
            *command, encoding=None, input=input, term_type='term' if use_terminal else None
        ) as process:
            proc = AsyncProcessAdapter(process, encoding=None if as_bytes else 'utf-8')
            if sudo and self._sudo_password:
                await proc.write_line(self._sudo_password)
                await proc.read_line()
            yield proc

    @override
    async def run(
        self,
        command: str,
        shell: bool = False,
        sudo: bool = False,
        as_bytes: bool = False,
        input: str | bytes | None = None,
    ) -> CompletedProcess:
        encoding = None if as_bytes else 'utf-8'

        async with self.create_process(
            command, shell, sudo=sudo, as_bytes=as_bytes, input=input
        ) as process:
            logger.debug(f'SSH proc started: {command!r} server: "{self._server_string}"')
            process = await process.wait()

        stdout, stderr = process.stdout, process.stderr

        if process.returncode == 0:
            logger.debug(f'SSH proc done: {command!r} server: "{self._server_string}"')
        else:
            logger.debug(
                f'SSH proc failed: {command!r} server: "{self._server_string}" '
                f'code: {process.returncode}'
            )

        if encoding:
            if isinstance(stdout, bytes):
                stdout = stdout.decode(encoding)
            elif not stdout:
                stdout = ''
            if isinstance(stderr, bytes):
                stderr = stderr.decode(encoding)
            elif not stderr:
                stderr = ''

            stdout, stderr = stdout.rstrip(), stderr.rstrip()
        else:
            stdout, stderr = stdout if stdout else b'', stderr if stderr else b''

        return CompletedProcess(
            command=command, returncode=process.returncode, stdout=stdout, stderr=stderr
        )


class AsyncSshConnection(AsyncConnection):
    def __init__(
        self,
        host: str,
        port: int = 22,
        username: str | None = None,
        password: str | None = None,
        sudo_password: str | None = None,
        connect_timeout: timedelta | None = None,
    ) -> None:
        self._host = host
        self._port = port or 22
        self._username = username
        self._password = password
        self._sudo_password = sudo_password
        self._connect_timeout = connect_timeout

    @override
    @asynccontextmanager
    async def session(self) -> AbstractAsyncContextManager[AsyncSshSession]:
        options = SSHClientConnectionOptions(
            username=self._username,
            password=self._password,
            known_hosts=None,
            connect_timeout=self._connect_timeout.total_seconds()
            if self._connect_timeout
            else None,
        )

        async with asyncssh.connect(
            host=self._host, port=self._port or (), options=options
        ) as connection:  # type: SSHClientConnection
            yield AsyncSshSession(
                connection=connection,
                server_string=f'{self._username}@{self._host}:{self._port}',
                sudo_password=self._sudo_password,
            )
