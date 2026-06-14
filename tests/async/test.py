import asyncio

from goastty.api import Task
from goastty.asyncrun import AsyncTask


async def main(c: int = 5) -> None:
    # Instantiate the payload data vector
    task = Task("ping", "-c", str(c), "google.com")

    # Bind the task payload to the async execution engine
    runner = AsyncTask(task)

    print({"status": "starting", "command": list(task)})

    # Dispatch the execution coroutine to the background event loop
    run_task = asyncio.create_task(runner.run(use_path=True))

    # Monitor engine execution while the background task is processing
    while not run_task.done():
        print("[Async Engine] Awaiting ping response... process actively running.")
        await asyncio.sleep(0.5)

    await run_task

    print(f"\n[Async Engine] Process finalized. PID tracked: {runner.pid}")
    print(f"Accumulated STDOUT buffer:\n{task.stdout.decode('utf-8', errors='ignore')}")


if __name__ == "__main__":
    asyncio.run(main(5))
