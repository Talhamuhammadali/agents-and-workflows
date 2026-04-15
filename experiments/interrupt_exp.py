"""Race pattern: if interrupt finishes first, cancel task A."""

import asyncio
import time


async def task_a(duration=10):
    print(f"Task A: starting (duration={duration}s)")
    await asyncio.sleep(duration)
    print("Task A: finished")
    return "A done"


async def interrupt(timeout=5):
    await asyncio.sleep(timeout)
    print("Interrupt: fired")
    return "interrupted"


async def run_with_interrupt(main_coro, interrupt_coro):
    """Approach 1: asyncio.wait + manual cancel."""
    a = asyncio.create_task(main_coro)
    i = asyncio.create_task(interrupt_coro)

    done, pending = await asyncio.wait({a, i}, return_when=asyncio.FIRST_COMPLETED)

    for p in pending:
        p.cancel()
        try:
            await p
        except asyncio.CancelledError:
            pass

    winner = done.pop()
    return "interrupted" if winner is i else winner.result()


class InterruptSignal(Exception):
    """Raised by interrupt_raising to trigger TaskGroup-wide cancellation."""


async def interrupt_raising(timeout=5):
    await asyncio.sleep(timeout)
    print("Interrupt: fired")
    raise InterruptSignal()


async def run_with_interrupt_tg(main_coro, interrupt_coro):
    """Approach 2: TaskGroup. interrupt_coro must raise InterruptSignal to win."""
    result_box = {}
    interrupt_task = None

    async def wrap_main():
        result_box["value"] = await main_coro
        interrupt_task.cancel()  # main won -> stop the interrupt

    interrupted = False
    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(wrap_main())
            interrupt_task = tg.create_task(interrupt_coro)
    except* InterruptSignal:
        interrupted = True
    if interrupted:
        return "interrupted"
    return result_box["value"]


async def timed_run(label, runner, main_coro, interrupt_coro):
    print(f"\n--- {label} ---")
    start = time.perf_counter()
    result = await runner(main_coro, interrupt_coro)
    elapsed = time.perf_counter() - start
    print(f"{label}: result={result!r}  elapsed={elapsed:.2f}s")


async def main():
    print("\n=== Approach 1: asyncio.wait ===")
    await timed_run("interrupt wins", run_with_interrupt, task_a(duration=10), interrupt(timeout=5))
    await timed_run("task wins", run_with_interrupt, task_a(duration=3), interrupt(timeout=10))

    print("\n=== Approach 2: TaskGroup ===")
    await timed_run("interrupt wins", run_with_interrupt_tg, task_a(duration=10), interrupt_raising(timeout=5))
    await timed_run("task wins", run_with_interrupt_tg, task_a(duration=3), interrupt_raising(timeout=10))


if __name__ == "__main__":
    asyncio.run(main())
