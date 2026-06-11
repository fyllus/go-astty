import threading
import time
from pathlib import Path

from goastty import syncrun


def main(c: int=5) -> None:
    # Initialize sequential task vector context
    task = syncrun.SyncTask("ping", "-Dv", "-c", str(c), "google.com")
    task.piper.path = Path.home()

    print({"status": "starting", "command": list(task)})

    # Dispatch the blocking execution thread to decouple I/O boundary tracking
    worker_thread = threading.Thread(target=task.run)
    worker_thread.start()

    # Core main loop monitors the state engine without stopping the thread runtime
    while task.piper.returncode is None:
        print("[Sync Engine] Processing execution pipeline... task locked in worker thread.")
        time.sleep(0.5)

    worker_thread.join()

    print(f"\n[Sync Engine] Process finalized with code: {task.piper.returncode}")
    print(f"Accumulated STDOUT buffer:\n{task.piper.stdout.decode('utf-8', errors='ignore')}")


if __name__ == "__main__":
    main(5)
