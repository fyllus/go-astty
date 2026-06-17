## Cross-Platform Low-Level Abstraction Reference

The `unified` module provides a low-level, zero-overhead abstraction layer that normalizes operating system execution primitives between Windows NT (`_winapi`) and POSIX (`posix_spawn`).

It exposes unified type payloads and underlying function wrappers, allowing upstream execution runtimes to interact with process handles and file descriptors interchangeably.

---

## 1. Core Data Structures

### `StartUpInfo`

* **Base**: `dict`
* **Description**: A unified metadata tracking container wrapper modeled after the Windows `STARTUPINFO` structure. It maps standard standard I/O streams and configuration flags into platform-specific layout constraints.

#### Initialization Configuration Layout

When instantiated, fields are automatically translated based on the current active platform flag (`IS_NT` or `IS_POSIX`):

| Variable / Key | Target (Windows NT) | Target (POSIX) |
| --- | --- | --- |
| `"dwFlags"` | Formats `STARTF_USESTDHANDLES` if handles exist | *Not used* |
| `"hStdInput"` | `_winapi.GetStdHandle` fallback | `0` (stdin file descriptor) fallback |
| `"hStdOutput"` | `_winapi.GetStdHandle` fallback | `1` (stdout file descriptor) fallback |
| `"hStdError"` | `_winapi.GetStdHandle` fallback | `2` (stderr file descriptor) fallback |
| `"pCwdDir"` | Set as string path or `Path` object | Set as string path or `Path` object |
| `"hDefEnv"` | *Not used* | Dictionary environment reference |

---

## 2. Platform Design Remapping

The layer branches internal execution paths at import time based on the host operating system, mapping raw handles directly into uniform dual-element tuples `tuple[int, int]`.

### Windows NT Internal Routines (`IS_NT`)

Directly invokes native Win32 system extensions using C-level extensions:

* **`_nt_close(handle)`**: Invokes `_winapi.CloseHandle`. Suppresses `OSError` if the targeted resource is already dead.
* **`_nt_pipe(attr, size)`**: Wraps `_winapi.CreatePipe` to create an anonymous I/O channel.
* **`_nt_waitpid(handle, opt)`**: Monitors process state using `_winapi.WaitForSingleObject`. If `opt == 1`, polls instantly with a zero timeout; otherwise, blocks indefinitely (`INFINITE`). Returns `(handle, exit_code)`.
* **`_nt_read(handle, buffer_size)`**: Calls `_winapi.ReadFile`. Gracefully intercepts `BrokenPipeError` and returns `(b"", None)` upon channel termination.
* **`_nt_spawn_process(cmd, args, si)`**: Quotes string array elements into a linear Win32 command-line string. Spawns via `_winapi.CreateProcess`, immediately releases the transient thread handle `ht`, and isolates the process handle.

### POSIX Internal Routines (`IS_POSIX`)

Directly invokes kernel system calls via fast C extensions:

* **`_posix_close(descriptor)`**: Drops file descriptors via `os.close`.
* **`_posix_pipe(attr, size)`**: Generates a standard reading/writing descriptor pair via `os.pipe`.
* **`_posix_waitpid(pid, opt)`**: Wraps `os.waitpid(pid, opt)`. Intercepts `ChildProcessError` returning `(pid, 0)`.
* **`_posix_read(descriptor, buffer_size)`**: Ingests bytes from the file descriptor via `os.read`.
* **`_posix_spawn_process(cmd, args, si)`**: Uses `shutil.which` to locate command binaries within system paths. Manipulates file descriptor bindings within the child process through `os.POSIX_SPAWN_DUP2` structures. Isolates directory context changes safely via an atomic `try...finally` layout:
1. Captures the parent process's active directory location using `os.getcwd()`.
2. Switches the workspace context to the requested directory target via `os.chdir(cwd)`.
3. Executes the process instantly using the low-overhead `os.posix_spawn` system call.
4. Restores the parent process's directory path inside the `finally` cleanup block.



---

## 3. Public Unified Interface

The following functions expose a uniform signature across all platforms, acting as the primary entry points for low-level process manipulation.

```python
def spawn(cmd: str | Path, args: list[str], si: StartUpInfo) -> tuple[int, int]

```

* **Description**: Spawns a system process using the fastest native platform routine.
* **Returns**: A tuple containing `(pid, handle)` on Windows, or `(pid, 0)` on POSIX layers.

```python
def waitpid(handle_or_descriptor: int, options: int = 0) -> tuple[int, int]

```

* **Description**: Halts or polls the system until the targeted process identifier or Win32 tracking handle finishes execution.
* **Returns**: A tracking tuple containing `(resource_id, exit_status)`.

```python
def read(handle_or_descriptor: int, buffer_size: int = 4096) -> tuple[bytes, int | None]

```

* **Description**: Extracts a raw binary chunk from an active standard input/output pipeline channel.
* **Returns**: A tracking tuple containing `(data_bytes, tracking_handle)`.

```python
def pipe(attr: Any = None, size: int | None = None) -> tuple[int, int]

```

* **Description**: Configures an anonymous operating system pipeline channel.
* **Returns**: A tracking tuple containing `(read_descriptor, write_descriptor)`.

```python
def close(handle_or_descriptor: int | None) -> None

```

* **Description**: Forcibly unbinds and cleans up a low-level operating system resource descriptor or process handle safely. Ignores empty or invalid identifiers (`None`, `-1`).

---

## 4. Operational Type Enforcement

### `check_all`

```python
def check_all(iterable: Iterable[Any], *args: type) -> Iterable[Any]

```

* **Description**: A generator that validates type inheritance for all items inside a pipeline sequence.
* **Error Control**: Immediately raises a `UnifiedRuntimeError` with a specialized `"unable_assignment"` case string if an element fails type validation, stopping invalid data from corrupting low-level OS operations.
