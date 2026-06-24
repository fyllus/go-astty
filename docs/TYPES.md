## High-Performance Memory Type & Vector Reference

The `types` module implements the underlying memory layouts and structural representations for the execution ecosystem. It ensures zero dynamic overhead using micro-allocation constraints, cross-compatibility with raw system primitives, and isolated stream routing map vectors.

---

## 1. High-Performance Structures

### Class: `Handle`

* **Description**: Lifecycle controller for non-blocking process tracking and operating system native channel descriptors.
* **Memory Architecture**: Implements `__slots__` explicitly to suppress runtime dynamic instance tracking dictionary creation (`__dict__`). It locks its memory space to three predefined attributes: `fd`, `_closed`, and `_completed`.
* **Polymorphism Hooks**:
* Overrides `__int__` and `__index__` protocols, providing seamless cast-free execution compatibility when passing instances directly into system C extensions or OS functions expecting raw integer file descriptors.



#### Operational Methods

* **`close()`**: Securely invalidates and drops the native low-level channel.
* **`read(buffer_size: int = 4096)`**: Directly drains a binary block package from the resource channel descriptor.
* **`sync_waitpid(options: int = 0)`**: Performs a non-blocking poll or blocking evaluation of the targeted resource once. Updates internal tracking states upon process exit.
* **`async_waitpid(options: int = 0, time_sleep: float = 0.01)`**: Cooperative pooling polling routine that checks target completion without locking the asynchronous loop.

---

## 2. Stream & Allocation Ingestion

### Class: `Buffer`

* **Base**: `bytearray`
* **Description**: Extensible, high-efficiency system I/O stream cache wrapper that operates directly on byte sequences.

#### Stream Processing Engine

The ingestion loop is split into dual execution models depending on whether a stateful `Handle` instance or a raw system descriptor integer is provided.

```python
# Synchronous ingestion pipeline
def sync_read(self, handle_or_descriptor: int | UnifiedHandle, buffer_size: int = 4096, autoclose: bool = False) -> None:

```

* **Mechanism**: Runs a continuous tight loop extraction, copying raw memory slices directly into its own instance sequence via `.extend()`. Flushes or closes descriptors automatically at EOF if `autoclose=True`.

```python
# Asynchronous ingestion pipeline
async def async_read(self, handle_or_descriptor: int | UnifiedHandle, buffer_size: int = 4096, autoclose: bool = False) -> None:

```

* **Mechanism**: Captures the active execution context loop via `asyncio.get_running_loop()`. It delegates blocking read operations to the background threadpool via `loop.run_in_executor`, keeping the asynchronous driver running at peak efficiency.

---

## 3. Data Vector Routing Maps

### Class: `Collector`

* **Base**: `dict`
* **Description**: An internal storage router specifically configured to link named system standard communication pipelines (`stdout`, `stderr`, `stdin`) to separate `Buffer` byte streams.
* **Data Guard Constraints**:
* Overrides `__setitem__` to prevent outside components from substituting standard channels with unmanaged types.
* Throws a `ExecutionError` with case string keys (`"invalid_assignment"`, `"index_not_found"`) if fields are altered arbitrarily.



### Class: `Task`

* **Base**: `list`
* **Description**: High-level execution payload controller. Inherits list structures to contain the complete sequence of targeted execution variables.

#### Interface Properties & Methods

* **`cmd()` / `args()**`: Split arguments cleanly, returning the root executable binary or parameter sequences respectively.
* **`env`: Connect directly to fields inside the internal `StartUpInfo` structural meta dictionary wrapper.
---

## 4. Architectural Boundaries

### Class: `Gateway`

* **Description**: Low-level operational boundary that isolates active channel readers and writers from the state engine.

#### Structural Attributes

* **`stdout_reader` / `stdout_writer**`: Statefully wrapped `Handle` instances tracking newly initialized cross-platform anonymous pipelines.
* **`stderr_reader` / `stderr_writer**`: Independent handle paths tracking error streams (initialized exclusively when `get_stderr=True`).
* **`pid` / `handle**`: Specialized property definitions exposing the system-level identification boundaries (`_pid` on POSIX, and `_handle` or `_pid` on Windows NT frameworks). Returns fallback configurations if checked prior to process assignment.
