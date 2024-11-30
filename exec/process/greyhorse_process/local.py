import asyncio
import shlex
from collections.abc import Callable
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from typing import override

from greyhorse.logging import logger

from .abc import AsyncConnection, AsyncSession, CompletedProcess
from .adapters import AsyncProcessAdapter


class AsyncLocalSession(AsyncSession):
    def __init__(self, sudo_password: str | None = None) -> None:
        self._sudo_password = sudo_password

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
        command = shlex.split(command, comments=True)

        if shell:
            entrypoint = asyncio.create_subprocess_shell
        else:
            entrypoint = asyncio.create_subprocess_exec

        if sudo:
            if self._sudo_password is None:
                logger.warning('Sudo used without the password')
            command = ['sudo', '-S', *command]

        if shell:
            command = [' '.join(command)]

        process = await entrypoint(
            *command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        proc = AsyncProcessAdapter(process, encoding=None if as_bytes else 'utf-8')
        if sudo and self._sudo_password:
            await proc.write_line(self._sudo_password)
            await proc.read_line(from_stderr=True)
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
        input = input.encode('utf-8') if isinstance(input, str) else input

        async with self.create_process(command, shell, sudo=sudo, as_bytes=as_bytes) as process:
            logger.debug(f'Local proc started: {command!r} pid: {process.wrapped.pid}')
            stdout, stderr = await process.wrapped.communicate(input=input)

        if process.returncode == 0:
            logger.debug(f'Local proc done: {command!r} pid: {process.wrapped.pid}')
        else:
            logger.debug(
                f'Local proc failed: {command!r} pid: {process.wrapped.pid} code: {process.returncode}'
            )

        if encoding:
            stdout = stdout.decode(encoding).rstrip() if stdout else ''
            stderr = stderr.decode(encoding).rstrip() if stderr else ''
        else:
            stdout, stderr = stdout if stdout else b'', stderr if stderr else b''

        return CompletedProcess(
            command=command, returncode=process.returncode, stdout=stdout, stderr=stderr
        )


class AsyncLocalConnection(AsyncConnection):
    def __init__(self, sudo_password: str | None = None) -> None:
        self._sudo_password = sudo_password

    @override
    @asynccontextmanager
    async def session(self) -> AbstractAsyncContextManager[AsyncLocalSession]:
        yield AsyncLocalSession(self._sudo_password)
