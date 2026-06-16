import subprocess
from time import time

from goastty.astty import exec_sync

# Configurações do ambiente de teste
ITERATIONS = 100
CMD = "ls"
ARGS = "-an"

print(f"Iniciando benchmark ({ITERATIONS} iterações)...")

# ==========================================================================
# Benchmark: Goastty SyncExecution
# ==========================================================================

start = time()
for _ in range(ITERATIONS):
    exec_sync(CMD, [ARGS])

goastty_total_time = time() - start

# Garante que os dados foram coletados com sucesso
# assert len(task.stdout) > 0, "Goastty falhou em coletar bytes"

# ==========================================================================
# Benchmark: Native Subprocess
# ==========================================================================
sub_total_time = 0.0
sub_args = [CMD, ARGS]

start = time()

for _ in range(ITERATIONS):
    res = subprocess.run(sub_args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

sub_total_time = time() - start

# Garante que os dados foram coletados com sucesso
# assert len(res.stdout) > 0, "Subprocess falhou em coletar bytes"

# ==========================================================================
# Resultados
# ==========================================================================
goastty_avg = (goastty_total_time / ITERATIONS) * 1000
sub_avg = (sub_total_time / ITERATIONS) * 1000

print("\n" + "=" * 40)
print("             BENCHMARK RESULTS            ")
print("=" * 40)
print(f"Goastty Sync (Média):  {goastty_avg:.4f} ms")
print(f"Subprocess (Média):    {sub_avg:.4f} ms")
print("-" * 40)

if goastty_avg < sub_avg:
    diff = ((sub_avg - goastty_avg) / sub_avg) * 100
    print(f"Goastty é {diff:.2f}% MAIS RÁPIDO que o subprocess nativo.")
else:
    diff = ((goastty_avg - sub_avg) / sub_avg) * 100
    print(f"Goastty é {diff:.2f}% MAIS LENTO que o subprocess nativo.")
print("=" * 40)
