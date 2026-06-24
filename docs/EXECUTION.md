## Execution State & Lifecycle Orchestration Reference

The `execution` module controls process pre-flight preparation, descriptor mapping, and stateful initialization. It coordinates how pipelines link transient data structures to the raw operating system primitives managed by the `unified` layer.

---

## 1. Functional Lifecycle Stages

The orchestration of a raw process is split into two lean stages to prevent resources from leaking or deadlock states on the standard I/O pipes.

### `init_startup`

```python
def init_startup(
    get_err: bool = False, config: StartUpInfo | None = None
) -> StartUpInfo:

```

* **Description**: Pre-allocates native anonymous pipelines and maps their writing and reading file descriptors into the `StartUpInfo` container.
* **Stream Binding Strategy**:
* Allocates a primary output channel via `pipe()`. The writing handle maps to `"hStdOutput"` (passed to the child process), and the reading descriptor maps to `"hReaderOutput"` (retained by the parent).
* If `get_err` is `False`, the child process's standard error channel (`"hStdError"`) is bound directly to the same writing descriptor as standard output, merging the streams at the kernel level for maximum performance.



### `post_startup`

```python
def post_startup(
    cmd: str | Path, args: list[str], env: dict | None, config: StartUpInfo
) -> tuple[int, int]:

```

* **Description**: Spawns the low-level operating system process and immediately performs a cleanup of the parent's copies of the child write descriptors.
* **Resource Isolation**:
* Forcibly closes the writing descriptor `"hStdOutput"` inside the parent process right after the process is spawned.
* If the error stream was allocated separately, its writer is also closed. This ensures that the parent reading loops encounter an End-Of-File (EOF) marker once the child process terminates, preventing infinite hang states.



---

## 2. Stateful Execution Architecture

### Class: `Execution`

* **Description**: High-level state I/O controller designed to act as a managed state machine wrapper over a `Task` lifecycle.

#### Property Interface

* **`pipe`** (`Gateway`): Exposes the current low-level gateway infrastructure tracking active stream descriptors and target process representations.
* **Error Control**: Accessing this property before invoking `.startup()` intentionally raises an `AttributeError` due to lazy variable initialization, preventing interactions with uninitialized descriptors.

#### Operational Methods

```python
def startup(self, get_stderr: bool = False) -> None:

```

* **Description**: Coordinates lazy initialization, registers write descriptors into the underlying task configuration vector, spawns the process image, and binds resource wrappers.
* **Internal Routine**:
1. Instantiates a new `Gateway` layout bound to the runtime, setting up required pipe structures under the hood.
2. Binds the gateway writer references directly to the target process parameters (`task.config`).
3. Invokes `spawn` passing the task's command string, expanded argument sequence, environment mappings, and configuration state.
4. Calls `.close()` on the parent process's copy of the write descriptors immediately. This ensures proper EOF propagation across pipelines.
5. Wraps raw integer system identifiers into specialized `Handle` tracking structures, binding them directly onto the active gateway container.



---

## 3. Resource Mapping Overview

The state machine lifecycle ensures precise tracking across both execution designs:

```
[ UnifiedTask ] ---> ( execution.startup ) ---> [ UnifiedGateway ]
                            │                          │
              (Allocates OS Pipes via unified)         ├──> stdout_reader / writer
                            │                          └──> stderr_reader / writer
                            ▼
              [ High-Performance Spawn ] ──> Wraps raw PID/Handle into UnifiedHandle

```
