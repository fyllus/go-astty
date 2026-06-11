import asyncio
from pathlib import Path

from goastty import asyncrun


async def main(c: int = 5) -> None:
    # Safe argument array context for native ping execution
    task = asyncrun.AsyncTask("ping", "-Dv", "-c", str(c), "google.com")
    task.piper.path = Path.home()

    print({"status": "starting", "command": list(task)})

    # Dispatch the execution coroutine to the background event loop
    run_task = asyncio.create_task(task.run())

    # Monitor engine execution while returncode remains unassigned
    while task.piper.returncode is None:
        print("[Async Engine] Awaiting ping response... process actively running.")
        await asyncio.sleep(0.5)

    await run_task

    print(f"\n[Async Engine] Process finalized with code: {task.piper.returncode}")
    print(f"Accumulated STDOUT buffer:\n{task.piper.stdout.decode('utf-8', errors='ignore')}")


if __name__ == "__main__":
    asyncio.run(main(5))
