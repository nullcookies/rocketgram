# Copyright (C) 2015-2019 by Vd.
# This file is part of RocketGram, the modern Telegram bot framework.
# RocketGram is released under the MIT License (see LICENSE).

import logging
from dataclasses import dataclass
from typing import Callable, Coroutine, AsyncGenerator, Union, List, TYPE_CHECKING

from .filters import FILTERS_ATTR, PRIORITY_ATTR, WAITER_ASSIGNED_ATTR, HANDLER_ASSIGNED_ATTR
from .filters import FilterParams, _check_sig
from ..baserouter import BaseRouter

if TYPE_CHECKING:
    from ...bot import Bot
    from ...context import Context
    from .proxy import BaseDispatcherProxy

logger = logging.getLogger('rocketgram.dispatcher')


@dataclass
class Handler:
    priority: int
    handler: Union[Callable, Coroutine, AsyncGenerator]
    filters: List[FilterParams]


DEFAULT_PRIORITY = 1024


def _register(what: List[Handler], handler_func: Callable[['Context'], None], default_priority: int):
    # Checking calling signature for handler_func.
    # object() means Context, passing to handler at runtime.
    assert _check_sig(handler_func, object()), \
        'Handler `%s` must take exactly one argument `ctx: Context`!' % handler_func.__name__

    assert not hasattr(handler_func, HANDLER_ASSIGNED_ATTR), 'Handler already registered!'
    assert not hasattr(handler_func, WAITER_ASSIGNED_ATTR), 'Already registered as waiter!'

    priority = getattr(handler_func, PRIORITY_ATTR, default_priority)
    assert isinstance(priority, int), 'Handler function has wrong priority!'

    filters = getattr(handler_func, FILTERS_ATTR, list())
    assert isinstance(filters, list), 'Handler function has wrong filters!'
    assert len(filters), 'Handler must have at least one filter!'

    what.append(Handler(priority, handler_func, filters))

    setattr(handler_func, HANDLER_ASSIGNED_ATTR, True)
    return handler_func


class BaseDispatcher(BaseRouter):
    def __init__(self, *, default_priority=DEFAULT_PRIORITY):
        self._init = list()
        self._shutdown = list()
        self._handlers: List[Handler] = list()
        self._pre: List[Handler] = list()
        self._post: List[Handler] = list()
        self._default_priority = default_priority
        self._bots: List['Bot'] = list()

    @property
    def default_priority(self):
        return self._default_priority

    def _resort_handlers(self):
        # sorting handlers by priority
        self._handlers = sorted(self._handlers, key=lambda handler: handler.priority)
        self._pre = sorted(self._pre, key=lambda handler: handler.priority)
        self._post = sorted(self._post, key=lambda handler: handler.priority)

    def from_proxy(self, proxy: 'DispatcherProxy'):
        self._init.extend(proxy.inits())
        self._shutdown.extend(proxy.shutdowns())
        self._handlers.extend(proxy.handlers())
        self._pre.extend(proxy.befores())
        self._post.extend(proxy.afters())

        # if handler added in runtime - resort handlers
        if len(self._bots):
            self._resort_handlers()

    async def init(self, bot: 'Bot'):
        logger.debug('Performing init...')

        if not len(self._bots):
            self._resort_handlers()

        self._bots.append(bot)

        for func in self._init:
            await func(self, bot)

    async def shutdown(self, bot: 'Bot'):
        logger.debug('Performing shutdown...')

        for func in reversed(self._shutdown):
            await func(self, bot)

        self._bots.remove(bot)

    def on_init(self):
        """Registers init"""

        def internal(func):
            self._init.append(func)
            return func

        return internal

    def on_shutdown(self):
        """Registers shutdown"""

        def internal(func):
            self._shutdown.append(func)
            return func

        return internal

    def handler(self, handler_func: Callable[['Context'], None]):
        """Registers handler"""

        r = _register(self._handlers, handler_func, self._default_priority)

        # if handler added in runtime - resort handlers
        if len(self._bots):
            self._resort_handlers()

        return r

    def before(self, handler_func: Callable[['Context'], None]):
        """Registers preprocessor"""

        r = _register(self._pre, handler_func, self._default_priority)

        # if handler added in runtime - resort handlers
        if len(self._bots):
            self._resort_handlers()

        return r

    def after(self, handler_func: Callable[['Context'], None]):
        """Registers postprocessor"""

        r = _register(self._post, handler_func, self._default_priority)

        # if handler added in runtime - resort handlers
        if len(self._bots):
            self._resort_handlers()

        return r

    async def process(self, ctx: 'Context'):
        """Process new request."""

        raise NotImplementedError
