## Cross-Platform Low-Level Abstraction Reference

The dynamic `platform` module provides a low-level, zero-overhead abstraction layer that normalizes operating system execution primitives between Windows NT (`_winapi`) and POSIX (`posix_spawn`).

It exposes unified type payloads and underlying function wrappers, allowing upstream execution runtimes to interact with process handles and file descriptors interchangeably.

---

## 1. Core Data Structures

### `StartUpInfo`

* **Base**: `dict`
* **Description**: A unified metadata tracking container wrapper modeled after the Windows `STARTUPINFO` structure. It maps standard standard I/O streams and configuration flags into platform-specific layout constraints.

#### Initialization Configuration Layout

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

### Windows NT Internal Routine

Directly invokes native Win32 system extensions using C-level extensions:

* **`close(handle)`**: Invokes `_winapi.CloseHandle`. Suppresses `OSError` if the targeted resource is already dead.
* **`pipe(attr, size)`**: Wraps `_winapi.CreatePipe` to create an anonymous I/O channel.
* **`waitpid(handle, opt)`**: Monitors process state using `_winapi.WaitForSingleObject`. If `opt == 1`, polls instantly with a zero timeout; otherwise, blocks indefinitely (`INFINITE`). Returns `(handle, exit_code)`.
* **`read(handle, buffer_size)`**: Calls `_winapi.ReadFile`. Gracefully intercepts `BrokenPipeError` and returns `(b"", None)` upon channel termination.
* **`spawn(cmd, args, si)`**: Quotes string array elements into a linear Win32 command-line string. Spawns via `_winapi.CreateProcess`, immediately releases the transient thread handle `ht`, and isolates the process handle.

### POSIX Internal Routines

Directly invokes kernel system calls via fast C extensions:

* **`close(descriptor)`**: Drops file descriptors via `os.close`.
* **`pipe(attr, size)`**: Generates a standard reading/writing descriptor pair via `os.pipe`.
* **`waitpid(pid, opt)`**: Wraps `os.waitpid(pid, opt)`. Intercepts `ChildProcessError` returning `(pid, 0)`.
* **`read(descriptor, buffer_size)`**: Ingests bytes from the file descriptor via `os.read`.
* **`spawn(cmd, args, si)`**: Uses `shutil.which` to locate command binaries within system paths. Manipulates file descriptor bindings within the child process through `os.POSIX_SPAWN_DUP2` structures. Isolates directory context changes safely via an atomic `try...finally` layout:
1. Captures the parent process's active directory location using `os.getcwd()`.
2. Switches the workspace context to the requested directory target via `os.chdir(cwd)`.
3. Executes the process instantly using the low-overhead `os.posix_spawn` system call.
4. Restores the parent process's directory path inside the `finally` cleanup block.
