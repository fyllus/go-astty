import threading
import time

from goastty.api import Task
from goastty.syncrun import SyncTask


def main(c: int = 5) -> None:
    # Initialize sequential task vector context
    task = Task("ping", "-c", str(c), "google.com")

    # Bind the task payload to the sync execution engine
    runner = SyncTask(task)

    print({"status": "starting", "command": list(task)})

    # Dispatch the blocking execution thread to decouple I/O boundary tracking
    worker_thread = threading.Thread(target=runner.run, kwargs={"use_path": True})
    worker_thread.start()

    # Core main loop monitors the state engine without stopping the thread runtime
    while worker_thread.is_alive():
        print("[Sync Engine] Processing execution pipeline... task locked in worker thread.")
        time.sleep(0.5)

    worker_thread.join()

    print(f"\n[Sync Engine] Process finalized. PID tracked: {runner.pid}")
    print(f"Accumulated STDOUT buffer:\n{task.stdout.decode('utf-8', errors='ignore')}")


if __name__ == "__main__":
    main(5)
