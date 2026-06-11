# go-astty

`go-astty` or `Gate of Asyncronous and Syncronous TTY`, is a modular process orchestration gate for seamless synchronous and asynchronous command-line executions in Python.

`go-astty` decouples process lifecycle management from standard I/O streams by introducing structured, data-driven pipelines. By abstracting execution payload contexts into self-contained Object vectors, it shifts execution responsibility from external engine hooks directly into individual Task runtimes.

## Architecture

The framework splits execution into two unified, object-oriented components:

* **Tasks (`_BaseTask`)**: Extended list containers acting as payload data vectors. They isolate the executable binary context, handle target system constraints via explicit pre-runtime structural gates (`validation`), and natively invoke their own execution cycles via `.run()`.
* **Pipers (`_BasePiper`)**: Isolated state engines tied directly to specific task envelopes to capture and track operational boundaries (`stdin`, `stdout`, `stderr`, paths, and exit return codes).

---

## Features

* **Self-Contained Runtimes**: Tasks are no longer passive configuration blocks passed to functional routines; execution logic is encapsulated directly within the task objects (`task.run()`).
* **Pre-Runtime Validation Gates**: Safe assertion tracks (`shutil.which`) evaluate process structure and binary integrity before booting processes to enforce immediate fail-fast mechanics.
* **Dual Object Engine Layout**: Mirrored execution architectures separating blocking synchronous behaviors (`syncrun.SyncTask`) and non-blocking asynchronous event routines (`asyncrun.AsyncTask`) cleanly under a predictable interface.

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
cd goastty
pip install .

```

---

## Usage Guide

### 1. Asynchronous Execution Pipeline

Perfect for long-running CLI integrations, microservices, or concurrent network-bound stream tracking.

```python
import asyncio
from pathlib import Path
from goastty import asyncrun

async def main():
    # Instantiate asynchronous task with payload arguments
    task = asyncrun.AsyncTask("ping", "-c", "5", "google.com")
    task.piper.path = Path.home()
    
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
from goastty import syncrun

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
* `validation()`: Evaluates process layout constraints and structural target command existence before booting.
* `run(stdin=None, kwargs)`: Abstract gateway implemented by runtime engines to drive process setups natively.
