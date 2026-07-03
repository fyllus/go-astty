    #!/usr/bin/env python3
import argparse
import re
import subprocess
import sys
from pathlib import Path
from typing import Generator

from goastty import exec_sync

COLORS_FILE = Path("/tmp/default-color.css")
PATTERN = re.compile(r"@define-color\s+(\S+)\s+([^;]+);")
CONFIG = Path.home() / ".config"


def get_gtk_theme() -> str:
    """Obtém o nome do tema GTK atual via GSettings."""
    try:
        res = subprocess.run(
            ["gsettings", "get", "org.gnome.desktop.interface", "gtk-theme"],
            capture_output=True,
            text=True,
            check=True,
        )
        return res.stdout.strip().strip("'\"")
    except subprocess.CalledProcessError:
        return "Adwaita"


def locate_gtk_css(theme_name: str) -> list[Path]:
    """Localiza os arquivos css de definição do tema (GTK3 e GTK4)."""
    search_paths = [
        Path.home() / ".themes" / theme_name / "gtk-4.0" / "gtk.css",
        Path.home() / ".themes" / theme_name / "gtk-3.0" / "gtk.css",
        Path("/usr/share/themes") / theme_name / "gtk-4.0" / "gtk.css",
        Path("/usr/share/themes") / theme_name / "gtk-3.0" / "gtk.css",
    ]
    return [p for p in search_paths if p.exists()]


class ColorType:
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


class Colors:
    def __init__(self, file_path: Path | None = None) -> None:
        self.file = file_path if file_path else COLORS_FILE
        self.colors = {}

    def __enter__(self):
        if not self.file.exists():
            sys.exit(127)

        with self.file.open("r") as f:
            for match in PATTERN.finditer(f.read()):
                name, value = match.groups()
                yield ColorType(name, value)

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def load(self, form="hex"):
        """Carrega o arquivo CSS populando o dicionário interno via context manager."""
        # Termos padrão utilizados pelo ecossistema GTK/Adwaita para elementos estruturais
        valid_keywords = [
            "theme_",
            "bg_",
            "fg_",
            "text_",
            "base_",
            "selected_",
            "insensitive_",
            "unfocused_",
            "borders",
            "wm_",
            "view_",
            "headerbar_",
            "card_",
            "dialog_",
            "popover_",
            "shade_",
            "scrollbar_",
            "accent_",
            "destructive_",
            "warning_color",
            "error_color",
            "success_color",
            "placeholder_",
        ]

        with self as color_stream:
            for color in color_stream:
                name_lower = color.name.lower()

                # Barreira: Só passa se o nome contiver termos estruturais do sistema
                if any(keyword in name_lower for keyword in valid_keywords):
                    self.colors[color.name] = color.to(form)


class Template(Colors):
    def __init__(
        self,
        file_path: Path,
        form: str = "hex",
        css_like: bool = True,
        ini_like: bool = False,
        block: tuple | None = ("*", "{", "}"),
        setter: str = "",
        prefix: str = "",
    ) -> None:
        super().__init__(file_path)
        self.load(form)

        self.div = ": " if css_like else " = " if ini_like else " "
        self.end = ";" if css_like else ""
        self.block = block
        self.setter = f"{setter} " if setter else ""
        self.prefix = prefix

    def lines(self) -> str:
        tab = "    " if self.block else ""
        return "\n".join(
            f"{tab}{self.setter}{self.prefix}{name}{self.div}{value}{self.end}"
            for name, value in self.colors.items()
        )

    def __str__(self) -> str:
        if self.block:
            start = (
                f"{self.block[0]} {self.block[1]}\n"
                if self.block[0]
                else f"{self.block[1]}\n"
            )
            return start + self.lines() + f"\n{self.block[2]}"
        return self.lines()


class GtkInterface:
    _prog = "gsettings"
    def __init__(self, schema: str = "org.gnome.desktop.interface") -> None:
        self._schema = schema
        self._key_values = {}
        for v in self.keys()
            _, buffer = exec_sync(self._prog, ["get", self._schema, v.strip()])
            self._key_values[v.strip()] = buffer.decode().strip('"').strip("'")

    def __getitem__(self, name: str):
        return self._key_values.get(name, None)

    def __setitem__(self, name: str, value: str):
        if (not name in self._key_values) or (not isinstance(name, str)):
            raise KeyError(f"{name} is not a valid key for {self._schema} schema")
        elif not isinstance(value, str):
            raise ValueError(f"{value} is not a valid value for key {name}")
        else:
            _, buffer = exec_sync(self._prog, ["set", self._schema, name, value])
            self._key_values[name] = value

    def keys(self):
        _, buffer = exec_sync(self._prog, ["list-keys", self._schema])
        return buffer.decode().splitlines()

    def schemas(self):
        _, buffer = exec_sync(self._prog, ["list-schemas"])
        return buffer.decode().splitlines()


class GtkFile:
    PATH = [
        Path.home() / ".local" / "themes",
        Path.home() / ".themes",
        Path("/usr/share/themes"),
    ]

    def __init__(self, theme_name: str, theme_font: str, theme_icon: str) -> None:
        parts = theme_font.strip().split(" ")
        self.theme_name = theme_name.strip("'").strip('"')
        self.theme_icon = theme_icon.strip("'").strip('"')
        self.theme_font = " ".join(parts[:-1])
        self.theme_font_size = parts[-1]

    def gtk_files(self, version: float = 4.0) -> Generator[Path, Path]:
        gtk_version = getattr(self, f"gtk-{version}")
        file = "gtk.css"
        for path in self.PATH:
            find = path / self.theme_name / gtk_version / file
            if find.resolve().exists():
                yield find.resolve()


def update_colors(file: Path = COLORS_FILE):
    """Varre o sistema buscando o tema atual e gera o arquivo colors.css centralizado."""
    theme = get_gtk_theme()
    paths = locate_gtk_css(theme)

    if not paths:
        print(
            f"Erro: Nenhum arquivo css encontrado para o tema '{theme}'.",
            file=sys.stderr,
        )
        sys.exit(1)

    extracted = Template(
        file_path=paths[0],
        form="alpha_rgb",
        css_like=False,
        block=None,
        setter="@define-color",
    )
    extracted.end = ";"

    # Alimenta o dicionário iterando nos arquivos restantes
    for path in paths[1:]:
        extracted.file = path
        extracted.load(form="alpha_rgb")

    # Correção do bug de avaliação booleana do objeto
    if not extracted.colors:
        print("Erro: Nenhuma cor pôde ser extraída.", file=sys.stderr)
        sys.exit(1)

    file.parent.mkdir(parents=True, exist_ok=True)
    with file.open("w", encoding="utf-8") as f:
        # Reclama o cabeçalho original com o nome do tema
        f.write(f"/* Gerado automaticamente a partir do tema: {theme} */\n\n")
        f.write(str(extracted))
        f.write("\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--path", type=Path, default=COLORS_FILE)
    parser.add_argument("--update", dest="update", action="store_true")

    group = parser.add_mutually_exclusive_group(required=False)
    group.add_argument("--sway", dest="as_sway", action="store_true")
    group.add_argument("--rasi", dest="as_rofi", action="store_true")
    group.add_argument("--foot", dest="as_foot", action="store_true")
    group.add_argument("--waybar", dest="as_waybar", action="store_true")
    group.add_argument("--default", dest="as_waybar", action="store_true")

    args = parser.parse_args()

    if args.update:
        update_colors(args.path)

    if args.as_sway:
        template = Template(
            args.path, form="hex", css_like=False, block=("set", "{", "}"), prefix="$"
        )
        sway = CONFIG / "sway/sway-colors-include.st"
        sway.write_text(str(template))
        print(template)

    elif args.as_rofi:
        template = Template(
            args.path,
            form="alpha_hex",
            css_like=True,
            block=("*", "{", "}"),
            prefix="--",
        )
        rofi = CONFIG / "rofi/rofi-colors-include.rasi"
        rofi.write_text(str(template).replace("_", "-"))
        print(str(template).replace("_", "-"))

    elif args.as_foot:
        template = Template(
            args.path,
            form="hex_raw",
            css_like=False,
            ini_like=True,
            block=("[colors]", "", ""),
        )
        foot = CONFIG / "foot/foot-colors-include.ini"
        foot.write_text(str(template))
        print(template)

    elif args.as_waybar:
        template = Template(
            args.path,
            form="hex",
            css_like=False,
            block=None,
            setter="@define-color",
        )
        template.end = ";"

        waybar = CONFIG / "waybar/waybar-colors-include.css"
        waybar.write_text(str(template))
        print(template)

    elif args.dafault:
        template = Template(
            args.path,
            form="alpha_rgb",
            css_like=False,
            block=None,
            setter="@define-color",
        )
        template.end = ";"
        print(template)


if __name__ == "__main__":
    main()
