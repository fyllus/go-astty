
# pytty

A professional, modular wrapper for seamless synchronous and asynchronous command-line executions in Python.

`pytty` decouples process lifecycle management from standard I/O streams by introducing structured, data-driven pipelines. By abstracting execution payload contexts into self-contained Object vectors, it shifts execution responsibility from external engine hooks directly into individual Task runtimes.

## Architecture

The framework splits execution into two unified, object-oriented components:
* **Tasks (`_BaseTask`)**: Extended list containers acting as payload data vectors. They isolate the executable binary context, handle target system constraints via explicit pre-runtime structural gates (`validation`), and natively invoke their own execution cycles via `.run()`.
* **Pipers (`_BasePiper`)**: Isolated state engines tied directly to specific task envelopes to capture and track operational boundaries (`stdin`, `stdout`, `stderr`, paths, and exit return codes).

---

## Features

* **Self-Contained Runtimes**: Tasks are no longer passive configuration blocks passed to functional routines; execution logic is encapsulated directly within the task objects (`task.run()`).
* **Pre-Runtime Validation Gates**: Safe assertion tracks (`shutil.which`) evaluate process structure and binary integrity before booting processes to enforce immediate fail-fast mechanics.
* **Dual Object Engine Layout**: Mirrored execution architectures separating blocking synchronous behaviors (`SyncTask`) and non-blocking asynchronous event routines (`AsyncTask`) cleanly under a predictable interface.

---

## Installation

To install directly from the source repository:

Clone from Codeberg:
```bash
git clone [https://codeberg.org/fyllus/pytty.git](https://codeberg.org/fyllus/pytty.git)
```

Clone from Github:
```bash
git clone [https://github.com/fyllus/pytty.git](https://github.com/fyllus/pytty.git)
```

Install:
```bash
cd pytty
pip install .
```

---

## Usage Guide

### 1. Asynchronous Execution Pipeline

Perfect for long-running CLI integrations, microservices, or concurrent network-bound stream tracking.

```python
import asyncio
from pathlib import Path
from pytty import asyncrun

async def main():
    # Instantiate asynchronous task with payload arguments
    task = asyncrun.AsyncTask("git", "log", "--oneline", "-n", "5")
    task.piper.path = Path("/path/to/repo")
    
    # Fire the self-contained non-blocking runtime
    await task.run()
    
    # Evaluate context matrices safely
    if task.piper.returncode == 0:
        print(task.piper.stdout.decode("utf-8"))
    else:
        print(f"Error: {task.piper.stderr.decode('utf-8')}")

if __name__ == "__main__":
    asyncio.run(main())

```

### 2. Synchronous Execution Pipeline

Ideal for local scripts, standard automation sequences, or linear operational pipelines.

```python
from pathlib import Path
from pytty import syncrun

def run_backup():
    # Build standard array configuration payload
    task = syncrun.SyncTask("tar", "-czf", "backup.tar.gz", "src/")
    task.piper.path = Path.cwd()
    
    # Invoke execution directly from the task payload instance
    task.run()
    
    print(f"Process finalized with code: {task.piper.returncode}")

if __name__ == "__main__":
    run_backup()

```

---

## API Specification

### Core Classes

#### `_BasePiper`

The logical data matrix tracking standard streams and execution boundaries.

* `stdout` / `stderr`: Automatic validation and mutation of incremental stream chunks (`bytearray`).
* `returncode`: Tracking vector for process termination status.
* `path`: Explicit execution context location directory (`pathlib.Path`).
* `shell`: Evaluates whether execution requires a target environment shell gateway.

#### `_BaseTask(list)`

An extended list structure executing process payload vectors.

* `prog`: Tracks the execution binary anchor context (`self[0]`).
* `args`: Slices away argument payloads safely (`self[1:]`).
* `validation()` / `validation`: Evaluates process layout constraints and structural target command existence before booting.
* `run(*args, kwargs)`: Abstract gateway implemented by runtime engines to drive process setups natively.
