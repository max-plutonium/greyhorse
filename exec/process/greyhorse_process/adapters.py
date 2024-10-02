from collections.abc import AsyncIterator, Iterator
from typing import AnyStr


class SyncProcessAdapter:
    def __init__(self, process, encoding: str | None = None) -> None:
        self._proc = process
        self._encoding = encoding
        self.stdin = process.stdin
        self.stdout = process.stdout
        self.stderr = process.stderr

    def read_line(self, from_stderr: bool = False, rstrip: bool = True) -> bytes | str:
        from_ = self._proc.stderr if from_stderr else self._proc.stdout
        data = from_.readline()
        if self._encoding and isinstance(data, bytes):
            data = data.decode(self._encoding)
        if rstrip:
            data = data.rstrip()
        return data

    def write_line(self, data: str | bytes) -> None:
        if self._encoding and isinstance(data, str):
            data = data.encode(self._encoding)
        data = data + (b'\n' if isinstance(data, bytes) else '\n')
        self._proc.stdin.write(data)
        self._proc.stdin.drain()

    def write_eof(self) -> None:
        self._proc.stdin.write_eof()
        self._proc.stdin.drain()

    class _ReadlineIter:
        def __init__(self, proc: 'SyncProcessAdapter', from_stderr: bool, rstrip: bool) -> None:
            self._proc = proc
            self._from_stderr = from_stderr
            self._rstrip = rstrip

        def __iter__(self) -> Iterator[AnyStr]:
            from_ = self._proc.stderr if self._from_stderr else self._proc.stdout
            while not from_.at_eof():
                yield self._proc.read_line(self._from_stderr, self._rstrip)

    def readline_iter(self, from_stderr: bool = False, rstrip: bool = True):
        return SyncProcessAdapter._ReadlineIter(self, from_stderr, rstrip)

    def wait(self):
        return self._proc.wait()

    @property
    def returncode(self):
        return self._proc.returncode

    @property
    def wrapped(self):
        return self._proc


class AsyncProcessAdapter:
    def __init__(self, process, encoding: str | None = None) -> None:
        self._proc = process
        self._encoding = encoding
        self.stdin = process.stdin
        self.stdout = process.stdout
        self.stderr = process.stderr

    async def read_line(self, from_stderr: bool = False, rstrip: bool = True) -> bytes | str:
        from_ = self._proc.stderr if from_stderr else self._proc.stdout
        data = await from_.readline()
        if self._encoding and isinstance(data, bytes):
            data = data.decode(self._encoding)
        if rstrip:
            data = data.rstrip()
        return data

    async def write_line(self, data: str | bytes) -> None:
        if self._encoding and isinstance(data, str):
            data = data.encode(self._encoding)
        data = data + (b'\n' if isinstance(data, bytes) else '\n')
        self._proc.stdin.write(data)
        await self._proc.stdin.drain()

    async def write_eof(self) -> None:
        self._proc.stdin.write_eof()
        await self._proc.stdin.drain()

    class _ReadlineIter:
        def __init__(
            self, proc: 'AsyncProcessAdapter', from_stderr: bool, rstrip: bool
        ) -> None:
            self._proc = proc
            self._from_stderr = from_stderr
            self._rstrip = rstrip

        async def __aiter__(self) -> AsyncIterator[AnyStr]:
            from_ = self._proc.stderr if self._from_stderr else self._proc.stdout
            while not from_.at_eof():
                yield await self._proc.read_line(self._from_stderr, self._rstrip)

    def readline_iter(self, from_stderr: bool = False, rstrip: bool = True):
        return AsyncProcessAdapter._ReadlineIter(self, from_stderr, rstrip)

    async def wait(self):
        return await self._proc.wait()

    @property
    def returncode(self):
        return self._proc.returncode

    @property
    def wrapped(self):
        return self._proc
