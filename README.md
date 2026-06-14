# Go-astty

Version: `0.2.0-a`

`go-astty` (Gate of Asynchronous and Synchronous TTY) is a modular, low-level process orchestration gate for seamless synchronous and asynchronous command-line executions in Python, featuring native cross-platform support (POSIX/Windows NT).

The framework decouples process lifecycle management from standard I/O streams by introducing structured, data-driven pipelines, shifting execution responsibility into dedicated execution runtimes.

---

## Project Status & Vision

This project is currently undergoing active structural optimization and architectural refinement. The primary objective is to evaluate alternative, highly efficient approaches for process spawning and I/O multiplexing.

Instead of relying on high-level standard abstractions, the focus is to map directly to the lowest possible native subsystem layers for both Windows NT (`_winapi` / `kernel32`) and POSIX (`os.fork` / `os.exec`), achieving maximum raw performance and minimal execution overhead.

---

## Architecture

The ecosystem splits execution into two lean, objective components:

* **Task (`Task`)**: An extended list container acting as the payload data vector. It isolates the executable binary context (`program`, `args`) and acts as the direct target for cumulative stream output buffers (`stdout` and `stderr` as `bytearray`).
* **Execution (`Execution`)**: The isolated state engine tied to a specific task instance to capture, track, and manage low-level native descriptors (`pipe`, `fork`, `waitpid`, `ReadFile`/`os.read`). It branches into two specialized runtime engines:
* `syncrun.SyncTask`: Drives linear, blocking synchronous workflows using native syscalls.
* `asyncrun.AsyncTask`: Drives non-blocking, cooperative event-loop routines using `asyncio`.

---
## Installation

To install directly from the source repository:

**Clone from Codeberg:**

```bash
git clone https://codeberg.org/Fyllus/go-astty.git

```

**Clone from GitHub:**

```bash
git clone https://github.com/fyllus/go-astty.git

```

**Install:**

```bash
cd go-astty
pip install .

```

---

## Usage Guide

### 1. Asynchronous Execution Pipeline (`AsyncTask`)

Perfect for long-running CLI integrations, concurrent network-bound stream tracking, or real-time execution without halting the asyncio event loop.

```python
import asyncio
from goastty.api import Task
from goastty.asyncrun import AsyncTask

async def main():
    # Instantiate argument payload vector
    task = Task("ping", "-c", "5", "google.com")
    
    # Bind payload context to the async execution engine
    runner = AsyncTask(task)
    
    # Fire the self-contained non-blocking runtime
    await runner.run(use_path=True)
    
    # Consume output buffers directly from the task payload instance
    print(task.stdout.decode("utf-8"))

if __name__ == "__main__":
    asyncio.run(main())

```

### 2. Synchronous Execution Pipeline (`SyncTask`)

Ideal for local scripts, standard automation sequences, or linear operational pipelines.

```python
from goastty.api import Task
from goastty.syncrun import SyncTask

def main():
    # Build array configuration payload
    task = Task("tar", "-czf", "backup.tar.gz", "src/")
    
    # Bind payload context to the blocking sync engine
    runner = SyncTask(task)
    
    # Invoke execution directly
    runner.run(use_path=True, is_vec=True)
    
    if len(task.stderr) > 0:
        print(f"Errors captured: {task.stderr.decode('utf-8')}")

if __name__ == "__main__":
    main()

```

---

## API Specification

> [!NOTE]
> For a comprehensive breakdown of low-level OS primitives, internal variables, structures, and native syscall wrappers, consult the separate [API Documentation](docs/API.md).

### `Task(list)`

An extended list structure holding process data payloads and stream buffers.

* **Properties**:
* `program` (`str`): Extracts the root binary target anchor (`self[0]`).
* `args` (`list[str]`): Complete sequence of parameter arguments.
* `stdout` (`bytearray`): Cumulative output stream buffer.
* `stderr` (`bytearray`): Cumulative error stream buffer.



### `_BaseExecution` (Abstract Class)

Low-level state controller managing OS-specific subsystem resource descriptors.

* **Properties / Attributes**:
* `pid` (`int`): Active system-level tracking process identifier.
* `handle` (`int`): Active win32 process tracking handle (Windows NT only).
* `reader` (`int`): Pipeline outbound reading descriptor.
* `writer` (`int`): Pipeline inbound writing descriptor.


* **Methods**:
* `run(use_path: bool, env: dict | None, is_vec: bool)`: Abstract gateway implemented by runtime engines to drive native lifecycle setups.
