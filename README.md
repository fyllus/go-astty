# Go-astty

Version: `0.3.0-a`

`go-astty` (Gate of Asynchronous and Synchronous TTY) is a minimalist, ultra-high-performance process orchestration layer for seamless synchronous and asynchronous command-line executions in Python.

By bypassing heavy high-level abstractions, it maps directly to native subsystem layers for Windows NT (`_winapi`) and POSIX (`posix_spawn`), matching the performance of CPython's native `subprocess` while providing decoupled, data-driven pipelines.

---

## Performance-Driven Architecture

The framework is stripped of runtime bloat to achieve near-zero execution overhead through critical low-level optimizations:

* **Fast Process Spawning (`posix_spawn`)**: Bypasses the costly overhead of `os.fork()` on POSIX layers. By using native `posix_spawn` primitives, it completely skips the interpreter's thread-lock/GIL and memory page tables duplication, reducing process creation time from **~2.7 ms down to ~1.04 ms** (matching native C performance). For implementation details, see [docs/UNIFIED.md](./docs/UNIFIED.md).
* **Memory-Optimized Lifecycle (`__slots__`)**: Core tracking objects discard dynamic instance dictionaries (`__dict__`). Lifecycles are bound directly to fixed memory structures, optimizing allocation inside hot execution loops. For structural details, see [docs/TYPES.md](./docs/TYPES.md).
* **Non-Blocking Deadlock Prevention**: Asynchronous pipelines run stream buffer consumption and process termination tracking concurrently via `asyncio.gather`, eliminating pipeline blockages caused by full OS pipe limits. For API details, see [docs/ASTTY.md](./docs/ASTTY.md).

---

## Technical Documentation Breakdown

For detailed architectural breakdowns, internal variables, and low-level subsystem mapping, consult the specialized documentation modules:

* [docs/ASTTY.md](./docs/ASTTY.md) – **Core API Reference**: Full breakdown of the Pure Functional Pipeline (`exec_sync`/`exec_async`) and Object-Oriented Pipeline (`SyncExecution`/`AsyncExecution`).
* [docs/TYPES.md](./docs/TYPES.md) – **Memory Type & Vector Reference**: Implementation details of high-performance memory structures (`UnifiedHandle`, `UnifiedIOBuffer`, `UnifiedTask`, `UnifiedGateway`).
* [docs/UNIFIED.md](./docs/UNIFIED.md) – **Low-Level Subsystem Abstraction**: Cross-platform abstractions normalizing Windows NT Win32 API calls and POSIX native syscall routines.
* [docs/EXECUTION.md](./docs/EXECUTION.md) – **State & Lifecycle Orchestration**: Pre-flight setups, pipe allocation algorithms, and process image spawning lifecycles (`init_startup`/`post_startup`).

---

## Installation

```bash
git clone https://github.com/fyllus/go-astty.git
cd go-astty
pip install .

```

---

## Quick Start Usage

### 1. Pure Functional Pipeline

Lightweight, stateless functional gateways for immediate execution and fast resource cleanup.

```python
import asyncio
from goastty.pipeline import exec_sync, exec_async

# Synchronous Sequential Pipeline
status_sync = exec_sync("tar", ["-czf", "backup.tar.gz", "src/"])

# Asynchronous Concurrent Pipeline
async def main():
    status_async = await exec_async("ping", ["-c", "3", "google.com"])

if __name__ == "__main__":
    asyncio.run(main())

```

### 2. Object-Oriented Pipeline

Stateful, data-driven context managers engineered for complex orchestration workflows.

```python
import asyncio
from goastty.types import SyncTask, AsyncTask
from goastty.pipeline import SyncExecution, AsyncExecution

# Synchronous OO Pipeline
task_sync = SyncTask("git", ["status"])
status_sync = SyncExecution(task_sync).run(get_stderr=True)

# Asynchronous OO Pipeline
async def main():
    task_async = AsyncTask("ls", ["-la"])
    status_async = await AsyncExecution(task_async).run(get_stderr=False)

if __name__ == "__main__":
    asyncio.run(main())

```
