import asyncio
import subprocess
from time import time

from goastty import (
    AsyncExecution,
    AsyncTask,
    SyncExecution,
    SyncTask,
)

# Benchmark configuration
ITERATIONS = 1000
CMD = "ls"
ARGS = "-an"

print(f"Starting benchmark ({ITERATIONS} iterations)...")

# ==========================================================================
# Benchmark: Goastty SyncExecution (Object-Oriented)
# ==========================================================================
start = time()

for _ in range(ITERATIONS):
    task_sync = SyncTask(CMD, ARGS)
    runner_sync = SyncExecution(task_sync)
    runner_sync.run(get_stderr=False)

goastty_sync_total = time() - start


# ==========================================================================
# Benchmark: Goastty AsyncExecution (Object-Oriented)
# ==========================================================================
async def run_async_benchmark():
    start_async = time()
    for _ in range(ITERATIONS):
        task_async = AsyncTask(CMD, ARGS)
        runner_async = AsyncExecution(task_async)
        await runner_async.run(get_stderr=False)
    return time() - start_async


goastty_async_total = asyncio.run(run_async_benchmark())

# ==========================================================================
# Benchmark: Native Subprocess
# ==========================================================================
sub_args = [CMD, ARGS]
start = time()

for _ in range(ITERATIONS):
    res = subprocess.run(sub_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

sub_total_time = time() - start

# ==========================================================================
# Results Compilation
# ==========================================================================
goastty_sync_avg = (goastty_sync_total / ITERATIONS) * 1000
goastty_async_avg = (goastty_async_total / ITERATIONS) * 1000
sub_avg = (sub_total_time / ITERATIONS) * 1000

print("\n" + "=" * 50)
print("                BENCHMARK RESULTS                ")
print("=" * 50)
print(f"Goastty Sync Execution (Avg):  {goastty_sync_avg:.4f} ms")
print(f"Goastty Async Execution (Avg): {goastty_async_avg:.4f} ms")
print(f"Subprocess Native (Avg):       {sub_avg:.4f} ms")
print("-" * 50)

# Performance delta comparison against native subprocess
for name, avg in [
    ("Goastty Sync", goastty_sync_avg),
    ("Goastty Async", goastty_async_avg),
]:
    if avg < sub_avg:
        diff = ((sub_avg - avg) / sub_avg) * 100
        print(f"{name} is {diff:.2f}% FASTER than native subprocess.")
    else:
        diff = ((avg - sub_avg) / sub_avg) * 100
        print(f"{name} is {diff:.2f}% SLOWER than native subprocess.")
print("=" * 50)
