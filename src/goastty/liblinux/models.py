import re
import shutil
from pathlib import Path

from goastty import SyncExecution, SyncTask


class ObjectScript:
    def __init__(self, script: Path | str = "") -> None:
        if isinstance(script, str):
            self._raw = script
        elif isinstance(script, Path) and script.exists():
            self._raw = script.read_text(encoding="utf-8")
        else:
            raise TypeError("Script must be <str> or <Path>")


class ObjectShell:
    def __init__(self, shell: str = "bash", cmd: str | ObjectScript = "") -> None:
        if not shutil.which(shell):
            raise ValueError(f"{shell} is not a valid shell")
        self.shell = SyncTask(shell, "-c")

        if isinstance(cmd, ObjectScript):
            self.shell.append(cmd._raw)
        elif isinstance(cmd, str):
            self.shell.append(cmd)
        else:
            raise TypeError("cmd must be <Script> or <str>")

    def run(self, get_err=False):
        return SyncExecution(self.shell).run(get_stderr=get_err)


class ObjectColor:
    def __init__(self, name: str, value: str) -> None:
        self.name = name
        self.r, self.g, self.b, self.a = self._parse(value.strip())

    def _parse(self, val: str) -> tuple:
        """Normaliza qualquer formato de entrada para canais inteiros e alpha float."""
        if val.startswith("#"):
            c = val[1:]
            if len(c) in (3, 4):
                c = "".join(x * 2 for x in c)
            r = int(c[0:2], 16)
            g = int(c[2:4], 16)
            b = int(c[4:6], 16)
            a = round(int(c[6:8], 16) / 255.0, 2) if len(c) == 8 else 1.0
            return r, g, b, a

        if val.startswith("rgb"):
            parts = [float(x.strip()) for x in re.findall(r"[-+]?\d*\.\d+|\d+", val)]
            r, g, b = map(int, parts[:3])
            a = parts[3] if len(parts) == 4 else 1.0
            return r, g, b, a

        return 0, 0, 0, 1.0

    def to(self, form="hex") -> str:
        """Converte de forma automática para o formato desejado."""
        if form == "hex":
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
        if form == "alpha_hex":
            return f"#{self.r:02x}{self.g:02x}{self.b:02x}{int(self.a * 255):02x}"
        if form == "hex_raw":
            return f"{self.r:02x}{self.g:02x}{self.b:02x}"
        if form == "alpha_hex_raw":
            return f"{int(self.a * 255):02x}{self.r:02x}{self.g:02x}{self.b:02x}"
        if form == "rgb":
            return f"rgb({self.r}, {self.g}, {self.b})"
        if form == "alpha_rgb":
            return f"rgba({self.r}, {self.g}, {self.b}, {self.a})"
        return f"#{self.r:02x}{self.g:02x}{self.b:02x}"
