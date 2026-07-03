import re

from goastty import exec_sync

CTRL_RULE = re.compile(r"Simple mixer control '([^']+)',(\d+)")
LIM_RULE = re.compile(r"Limits: Playback (\d+) - (\d+)")
CHN_RULE = re.compile(
    r"(Front Left|Front Right|Mono): Playback (\d+) \[(\d+)%\] \[(on|off)\]"
)

class Channel:
    def __init__(
        self,
        parent: Controller,
        name: str,
        absolute: int,
        percentage: int,
        active: bool,
    ) -> None:

        self._parent = parent
        self._name = name
        self._absolute = absolute
        self._percentage = percentage
        self._active = active

    @property
    def mute(self):
        return not self._active

    @mute.setter
    def mute(self, value: bool = True):
        action = "mute" if value else "unmute"
        self._active = action == "unmute"
        name, _ = self._parent.interface
        exec_sync("amixer", ["sset", name, action, f"{self._name.split()[-1].lower()}"])

    @property
    def percentage(self):
        return self._percentage

    @percentage.setter
    def percentage(self, value: int):
        value = max(0, min(100, value))
        self._percentage = value
        name, _ = self._parent.interface
        exec_sync(
            "amixer",
            ["sset", name, f"{value}%", f"{self._name.split()[-1].lower()}"],
        )

    @property
    def absolute(self):
        return self._absolute

    @absolute.setter
    def absolute(self, value: int):
        name, _ = self._parent.interface
        mn, mx = self._parent.limit
        value = max(mn, min(mx, value))
        self._absolute = value
        exec_sync(
            "amixer",
            ["sset", name, f"{value}", f"{self._name.split()[-1].lower()}"],
        )

    def scroll(self, value: int, absolute=False):
        if absolute:
            new = self.absolute + value
            self.absolute = new
        else:
            new = self.percentage + value
            self.percentage = new


class Controller:
    def __init__(self) -> None:
        pass

    @property
    def interface(self):
        return getattr(self, "_name", "Master"), getattr(self, "_index", 0)

    @interface.setter
    def interface(self, value: str):
        match = CTRL_RULE.search(value.strip())
        if match:
            setattr(self, "_name", match.group(1))
            setattr(self, "_index", int(match.group(2)))

    @property
    def limit(self):
        return getattr(self, "_limit", (0, 65536))

    @limit.setter
    def limit(self, value: str):
        match = LIM_RULE.search(value)
        if match:
            setattr(self, "_limit", (int(match.group(1)), int(match.group(2))))

    @property
    def channels(self):
        return getattr(self, "_channels", {})

    @channels.setter
    def channels(self, value: str):
        if not hasattr(self, "_channels"):
            self._channels = {}

        match = CHN_RULE.search(value)
        if match:
            chn = Channel(
                parent=self,
                name=match.group(1),
                absolute=int(match.group(2)),
                percentage=int(match.group(3)),
                active="on" in match.group(4),
            )
            self._channels[chn._name] = chn


class Mixer:
    def __init__(self, name: str | None = None) -> None:
        if not name:
            _, amixer = exec_sync("amixer", [])
            for line in amixer.decode().splitlines():
                match = CTRL_RULE.search(line.strip())
                if match:
                    found = match.group(1)
                    setattr(self, found, self._get(found))
        else:
            setattr(self, name, self._get(name))

    def _get(self, name: str):
        _, amixer = exec_sync("amixer", ["sget", name])
        output = Controller()
        lines = amixer.decode().splitlines()
        for line in lines:
            output.interface = line
            output.limit = line
            output.channels = line
        return output

    def __getitem__(self, name: str):
        return self._get(name)
