from collections import defaultdict
from collections.abc import Callable, Mapping
from typing import TypeVar

from greyhorse.logging import logger
from greyhorse.result import Result
from greyhorse.utils.invoke import invoke_async, invoke_sync

MessageType = TypeVar('MessageType')
CommandHandler = Callable[[MessageType], Result]
EventHandler = Callable[[MessageType], None]


class SyncMessageBus:
    def __init__(
        self,
        cmd_handlers: Mapping[type[MessageType], CommandHandler] | None = None,
        event_handlers: Mapping[type[MessageType], list[EventHandler]] | None = None,
    ) -> None:
        self._cmd_handlers = cmd_handlers or dict()
        self._event_handlers = event_handlers or defaultdict(list)

    def add_command_handler(
        self, message_type: type[MessageType], handler: CommandHandler
    ) -> None:
        self._cmd_handlers[message_type] = handler

    def add_event_handler(self, message_type: type[MessageType], handler: EventHandler) -> None:
        self._event_handlers[message_type].append(handler)

    def handle_command(self, message: MessageType) -> Result:
        if handler := self._cmd_handlers.get(type(message)):
            return invoke_sync(handler, message)
        raise LookupError()

    def handle_event(self, message: MessageType) -> None:
        for handler in self._event_handlers[type(message)]:
            try:
                invoke_sync(handler, message)
            except Exception as e:
                logger.exception(str(e))
                continue


class AsyncMessageBus:
    def __init__(
        self,
        cmd_handlers: Mapping[type[MessageType], CommandHandler] | None = None,
        event_handlers: Mapping[type[MessageType], list[EventHandler]] | None = None,
    ) -> None:
        self._cmd_handlers = cmd_handlers or dict()
        self._event_handlers = event_handlers or defaultdict(list)

    def add_command_handler(
        self, message_type: type[MessageType], handler: CommandHandler
    ) -> None:
        self._cmd_handlers[message_type] = handler

    def add_event_handler(self, message_type: type[MessageType], handler: EventHandler) -> None:
        self._event_handlers[message_type].append(handler)

    async def handle_command(self, message: MessageType) -> Result:
        if handler := self._cmd_handlers.get(type(message)):
            return await invoke_async(handler, message)
        raise LookupError()

    async def handle_event(self, message: MessageType) -> None:
        for handler in self._event_handlers[type(message)]:
            try:
                await invoke_async(handler, message)
            except Exception as e:
                logger.exception(str(e))
                continue
