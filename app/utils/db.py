from __future__ import annotations

import asyncio
from typing import Any, Callable


async def run_db(callable_obj: Callable[[], Any]) -> Any:
    return await asyncio.to_thread(callable_obj)
