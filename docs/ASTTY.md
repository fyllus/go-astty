## High-Performance Core API Reference

The `goastty` core API isolates low-level operating system process routines from high-level data abstractions. 
It provides two architectural entry points to process orchestration: a stateless **Pure Functional Pipeline** and a stateful, data-driven **Object-Oriented Pipeline**.

---

## 1. Pure Functional Pipeline

Stateless functional gateways engineered for immediate system process spawning, inline stream consumption, and instantaneous resource teardown.

### `exec_sync`

```python
def exec_sync(
    cmd: str | Path,
    args: list[str],
    env: dict | None = None,
    config: StartUpInfo = StartUpInfo(),
    get_err: bool = False,
) -> int:

```

* **Description**: Spawns a system process and sequentially flushes standard output (and optionally standard error) into a transient memory buffer. Blocks the main thread until the process terminates.
* **Arguments**:
* `cmd`: Absolute binary path or system command name.
* `args`: Sequential array of string parameters passed to the process.
* `env`: Optional environment dictionary overrides. Defaults to inherited `os.environ`.
* `config`: A configured `StartUpInfo` dict instance controlling descriptor inheritance and execution configurations.
* `get_err`: When `True`, forces the initialization and reading of the standard error (`stderr`) pipeline channel.


* **Returns**: `int` representing the final system termination exit code status.

### `exec_async`

```python
async def exec_async(
    cmd: str | Path,
    args: list[str],
    env: dict | None = None,
    config: StartUpInfo = StartUpInfo(),
    get_err: bool = False,
) -> int:

```

* **Description**: Non-blocking asynchronous equivalent of `exec_sync`. Utilizes cooperative event-loop concurrency via `asyncio.gather` to drive low-level descriptor reads and process wait states simultaneously.
* **Concurrency Architecture**:
* Prevents OS pipe-buffer deadlocks by draining `stdout` (and `stderr`) concurrently while evaluating `waitpid`.


* **Returns**: Coroutine yielding an `int` process termination exit code status.

---

## 2. Object-Oriented Pipeline

Stateful execution wrappers mapping a distinct data payload tracking vector (`UnifiedTask`) to an isolated machine controller (`Execution`).

### Class: `SyncTask`

* **Base**: `UnifiedTask`
* **Description**: Synchronous targeted pipeline context payload wrapper. Encapsulates process metadata variables, binaries, arguments, and synchronous buffer targets.

### Class: `SyncExecution`

* **Base**: `Execution`
* **Description**: Master synchronous execution controller driving linear, blocking workflows.
* **Methods**:
* `run(get_stderr: bool = False) -> int`: Consumes low-level descriptors to termination sequentially.
1. Triggers `self.startup()` to bind low-level descriptors.
2. Sequentially executes `sync_read` operations on the pipe reader channels.
3. Blocks on the target native identifier via `sync_waitpid()`.
4. Automatically flushes and closes active handles.





### Class: `AsyncTask`

* **Base**: `UnifiedTask`
* **Description**: Asynchronous targeted pipeline context payload wrapper. Encapsulates data targets and maps async-compatible buffer states.

### Class: `AsyncExecution`

* **Base**: `Execution`
* **Description**: Master asynchronous execution controller driving non-blocking, cooperative event-loop routines.
* **Methods**:
* `async run(get_stderr: bool = False) -> int`: Non-blocking, concurrent execution orchestration using an underlying `asyncio` pool loop.
1. Triggers `self.startup()` to assign non-blocking descriptors.
2. Resolves cross-platform identities (`pipe.handle` for NT, `pipe.pid` for POSIX).
3. Wraps `async_read` loops and the underlying `async_waitpid` state into a single atomic `asyncio.gather` pipeline.
4. Releases handle claims and yields the system exit status code.





---

## 3. Internal Lifecycle & Optimization Architecture

The pipelines rely on an optimal internal low-level routine to bridge execution down to the OS kernel without adding interpretation latency:

| Step | Operation | Platform Specific Routine |
| --- | --- | --- |
| **1. Initialization** | `init_startup` | Resolves standard handles, initializes anonymous pipelines, and tracks reader/writer file descriptors. |
| **2. Spawning** | `post_startup` | Bypasses `os.fork` overhead on POSIX using high-performance `posix_spawn` primitives. On Windows NT, delegates directly to `_winapi.CreateProcess`. |
| **3. Memory Allocation** | Tracking | Shared descriptors rely on `__slots__` via `UnifiedHandle` to prevent dynamic namespace generation (`__dict__`). |
| **4. IO Ingestion** | `UnifiedIOBuffer` | Automatically drains internal OS pipe streams directly into raw byte-arrays without encoding conversions during the hot loop. |
