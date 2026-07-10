import json
import re
from pathlib import Path

from goastty.unix.models import ObjectCPUData, ObjectMemData


class CPU:
    def __init__(self) -> None:
        self.CPU = []
        processor_info = {}

        for line in Path("/proc/cpuinfo").read_text().splitlines():
            if not line.strip():
                if processor_info:
                    self.CPU.append(processor_info)
                    processor_info = {}
                continue

            label, _, value = line.partition(":")
            label = label.strip().replace(" ", "_")
            if label:
                processor_info[label] = ObjectCPUData(value.strip())

        if processor_info:
            self.CPU.append(processor_info)

    def __str__(self) -> str:
        formatted = [{k: str(v) for k, v in core.items()} for core in self.CPU]
        return json.dumps(formatted, indent=3)


class SystemInfo:
    def __init__(self) -> None:
        self.STAT = {}
        self._load_uptime()
        self._load_loadavg()

    def _load_uptime(self) -> None:
        uptime_data = Path("/proc/uptime").read_text().split()
        if uptime_data:
            self.STAT["Uptime_seconds"] = ObjectCPUData(uptime_data[0])
            self.STAT["Idle_seconds"] = ObjectCPUData(uptime_data[1])

    def _load_loadavg(self) -> None:
        load_data = Path("/proc/loadavg").read_text().split()
        if len(load_data) >= 3:
            self.STAT["Load_1m"] = ObjectCPUData(load_data[0])
            self.STAT["Load_5m"] = ObjectCPUData(load_data[1])
            self.STAT["Load_15m"] = ObjectCPUData(load_data[2])

    def __str__(self) -> str:
        return json.dumps({k: str(v) for k, v in self.STAT.items()}, indent=3)


class Memory:
    PATTERN = re.compile(r"^([^:]+):\s*(\d+)(?:\s+([a-zA-Z]+))?")

    def __init__(self) -> None:
        self.MEM = {}
        for line in Path("/proc/meminfo").read_text().splitlines():
            if match := self.PATTERN.match(line):
                raw_label = match.group(1).strip()

                label = raw_label.replace("(", "_").replace(")", "")
                label = re.sub(
                    r"(?<!^)(?=[A-Z][a-z])|(?<=[a-z0-9])(?=[A-Z])", "_", label
                )
                label = re.sub(r"_+", "_", label).lower().strip("_")

                value = match.group(2)
                ext = match.group(3) or ""

                data = ObjectMemData(f"{value} {ext}".strip())
                self.MEM[label] = data
                setattr(self, label, self.MEM[label])

    def using(self, format="percent"):
        avail = int(getattr(self, "mem_available"))
        total = int(getattr(self, "mem_total"))
        used = total - avail
        match format:
            case "percent":
                return round(used / total, 2) * 100
            case "absolute":
                return used

    def __str__(self) -> str:
        return json.dumps({k: str(v) for k, v in self.MEM.items()}, indent=3)
