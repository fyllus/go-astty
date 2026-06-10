```markdown
# pytty

A professional, modular wrapper for seamless synchronous and asynchronous command-line executions in Python.

`pytty` decouples process lifecycle management from standard I/O streams by introducing structured, data-driven pipelines. By abstracting `subprocess` and `asyncio` sub-processes into unified Task and Piper objects, it ensures predictable state management, stream encapsulation, and reusable execution contexts.

## Architecture

The framework splits execution into two clear components:
* **Tasks (`_BaseTask`)**: Array-driven vectors that isolate the executable binary from its trailing argument context.
* **Pipers (`_BasePiper`)**: Independent state containers that govern data streams (`stdin`, `stdout`, `stderr`), execution pathways, and return statuses.

---

## Features

* **Dual Engine Layout**: Fully mirrored APIs for both synchronous blocking pipelines and asynchronous non-blocking event loops.
* **State-Aware Stream Tracking**: Output metrics (`stdout`, `stderr`) are accumulated cleanly as mutable `bytearray` slices directly inside the execution envelope.
* **Context Isolation**: Working paths, environment shells, and execution hooks are independent variables tied specifically to each task wrapper.

---

## Installation

To install directly from the source repository:

```bash
git clone https://github.com/fyllus/pytty.git
cd pytty
pip install .

```

---

## Usage Guide

### 1. Asynchronous Execution Pipeline

Perfect for long-running CLI integrations, microservices, or network-bound streams requiring non-blocking chunk consumption.

```python
import asyncio
from pathlib import Path
from pytty.async_engine import AsyncTask, shell

async def main():
    # Instantiate task with binary and safe argument arrays
    task = AsyncTask("git", "log", "--oneline", "-n", "5")
    
    # Configure context through the task pipeline manager
    task.piper.path = Path("/path/to/repo")
    
    # Run the non-blocking engine
    await shell(task)
    
    # Extract structural metrics cleanly
    if task.piper.returncode == 0:
        print(task.piper.stdout.decode("utf-8"))
    else:
        print(f"Error: {task.piper.stderr.decode('utf-8')}")

if __name__ == "__main__":
    asyncio.run(main())

```

### 2. Synchronous Execution Pipeline

Ideal for scripting, automation utilities, or linear operations where downstream computations strictly depend on immediate sequential process finalization.

```python
from pathlib import Path
from pytty.sync_engine import SyncTask, shell

def run_backup():
    # Initialize task structures sequentially
    task = SyncTask("tar", "-czf", "backup.tar.gz", "src/")
    task.piper.path = Path.cwd()
    
    # Execute through the blocking runtime engine
    shell(task)
    
    print(f"Process finalized with code: {task.piper.returncode}")

if __name__ == "__main__":
    run_backup()

```

---

## API Specification

### Core Classes

#### `_BasePiper`

The logical tracking layer for state boundaries.

* `stdout` / `stderr`: Automatic validation and expansion of incoming `bytes` or `bytearray` buffers.
* `returncode`: Tracks the precise exit state integer.
* `path`: Extends native `pathlib.Path` structures for strict directory containment.

#### `_BaseTask(list)`

An extended list structure designed for strict argument indexing.

* `prog`: Tracks the execution binary (always index `[0]`).
* `args`: Slices away arguments safely (always slices `[1:]`).
* `callback`: Safe validator for processing completion triggers.

```

```
