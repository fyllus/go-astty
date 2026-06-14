# Core API Specification

This document contains the complete technical specification for the low-level cross-platform process orchestration API primitives.

---

## Global Subsystem Identifiers

The module exposes platform flags and standard stream replacement constants at the root level:

* `is_nt` (`bool`): Evaluates `True` if the host operating system runtime is Windows NT.
* `is_posix` (`bool`): Evaluates `True` if the host operating system matches POSIX compliance standards.
* `PIPE` (`int`): Constant mapping (`-1`) indicating standard pipeline generation request.
* `STDOUT` (`int`): Constant mapping (`-2`) redirection target matching stdout address space.
* `DEVNULL` (`int`): Constant mapping (`-3`) targeting system null device file descriptor.

---

## Custom Exceptions

### `AssignmentError`

Bases: `Exception`

Raised during invalid property mutations or unexpected type assignment attempts within low-level platform gateways.

---

## Platform-Specific Primitives

### Windows NT Subsystem Components

The following wrappers are conditionally bound only when `is_nt` evaluates to `True`:

#### `ProcessParam(dict)`

Extends native `dict`. Structured wrapper mirroring parameters required by `_winapi.CreateProcess`.

* Key mappings: `application_name`, `command_line`, `proc_attrs`, `thread_attrs`, `inherit_handles`, `creation_flags`, `env_mapping`, `current_directory`, `startup_info`.

#### `StartUpInfo(dict)`

Extends native `dict`. Structured configuration map targeting the native Win32 `STARTUPINFO` layout. Automatically queries system standard handle states via `_winapi.GetStdHandle` if fallback parameters are omitted.

---

## Low-Level Operational Gateways

### `pipe(pipe_attr: Any = None, size: int = 0) -> tuple[int, int]`

Generates an operating system-specific anonymous bidirectional pipeline channel.

* **Returns**: A tuple containing `(read_handle, write_handle)`. Uses `_winapi.CreatePipe` on Windows NT and `os.pipe` on POSIX.

### `close(handle_or_fd: int | None) -> None`

Closes a native subsystem resource descriptor or process/thread handle safely. Ignores empty or invalid identifiers (`None`, `-1`).

### `fork(param: ProcessParam | None = None) -> tuple[int | None, int | None, int, Any]`

Splits target process lifecycle division space natively.

* **Windows NT Execution**: Spawns process using `_winapi.CreateProcess`. Returns `(process_handle, thread_handle, pid, thread_id)`.
* **POSIX Execution**: Executes standard `os.fork()`. Returns `(None, None, pid, None)`.

### `waitpid(pid_or_handle: int, options: int = 0) -> tuple[int, int]`

Awaits the exit status or signal notification from an explicit target process handle or system PID.

* **Windows NT Logic**: Converts `options == 1` into a non-blocking timeout checkout via `_winapi.WaitForSingleObject`.
* **POSIX Logic**: Forwards directly to `os.waitpid`, catching detached or invalid references via `ChildProcessError`.

### `duplicate(source_fd: int, target_fd: int = 1, inheritable: bool = True) -> int`

Duplicates target system descriptor parameters. Mutates handle inherit flag maps using `kernel32.SetHandleInformation` on Windows NT or `os.dup2` on POSIX.

### `predirect(handle_or_fd: int) -> Any`

Configures standard stream redirection parameters.

* **POSIX**: Force-redirects file descriptor target destinations directly to native standard outputs `1` and `2`, closing original descriptors immediately.
* **Windows NT**: Generates a preconfigured `StartUpInfo` packet targeting destination handles.

### `read(handle_or_fd: int, buffer_size: int = 4096) -> tuple[bytes, int | None]`

Reads an isolated raw data chunk out of a native system stream resource. Catches `BrokenPipeError` and returns empty `bytes` when pipelines collapse.

---

## Data Structures

### `Task(list)`

Bases: `list`

An extended, data-driven vector managing the executable string sequence and accumulating standard stream data buffers.

#### Properties

* `program` (`str`): The target binary execution hook address (`self[0]`).
* `args` (`list[str]`): Complete parameter string sequence passed to execution.
* `stdout` (`bytearray`): Read-only cumulative byte array containing captured process standard output.
* `stderr` (`bytearray`): Read-only cumulative byte array containing captured process standard error.

#### Setters

* `stdout(value: bytes | bytearray)`: Appends incoming data fragments to the underlying `_stdout` storage array.
* `stderr(value: bytes | bytearray)`: Appends incoming data fragments to the underlying `_stderr` storage array.

---

## Abstract Infrastructure Layout

### `_BaseExecution(ABC)`

Bases: `abc.ABC`

The underlying abstract hardware abstraction layer (HAL) interface controlling pipeline bindings, system execution state trackers, and generic chunk-reading loops.

#### Properties

* `pid` (`int`): Active low-level operational tracking process system identifier.
* `writer` (`int`): Inbound pipeline descriptor tracking system write targets.
* `reader` (`int`): Outbound pipeline descriptor tracking system read targets.

#### Internal Methods

* `_chunk_read() -> None`: Synchronous blocking pipeline drain routine. Populates `task.stdout` buffers incrementally until EOF.
* `_chunk_read_async() -> Coroutine`: Asynchronous non-blocking loop driving off-thread chunk tracking via `asyncio.get_running_loop().run_in_executor`.

#### Abstract Methods

* `run(use_path: bool, env: dict | None, is_vec: bool) -> Any`: To be implemented by target runtime execution engines to drive process initialization pipelines natively.

---

## Subsystem Execution Architectures

The framework uses environment evaluation gates to branch the concrete `Execution` wrapper dynamically across distinct OS execution layouts.

### Windows NT Subsystem Execution Engine

*Condition: `if is_nt:*`

#### `Execution(_BaseExecution, ABC)`

Implements core Win32 process spawning workflows using `STARTUPINFO` and token mapping logic.

* **Properties**:
* `handle` (`int`): Active native tracking kernel process handle object.


* **Internal Methods**:
* `_setup_nt_pipeline() -> None`: Orchestrates the precise arrangement of anonymous pipelines, configures non-inheritable reading boundaries, formats command string line blocks, and executes the underlying process setup.



---

### POSIX Subsystem Execution Engine

*Condition: `if is_posix:*`

#### `Execution(_BaseExecution, ABC)`

Implements low-level POSIX execution structures using the standard `fork-and-exec` archetype pattern.

* **Internal Methods**:
* `_try_exec(use_path: bool, env: dict | None, is_vec: bool) -> tuple[bool, Any]`: Dispatches internal calls to native `os.exec` variants (`execv`, `execve`, `execvp`, `execl`, etc.) dynamically, capturing system execution runtime crashes.
* `_child_side(use_path: bool, env: dict | None, is_vec: bool) -> None`: Finalizes descriptor redirection layout actions inside the fork split before replacing the current memory space with the chosen program binary. Ends execution via `sys.exit(127)` if lookup pipelines miss targets.
