"""Prepare the configured FIFA installation for Boxedwine (Python 3.11+)."""
import configparser
import hashlib
import json
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile

HERE = Path(__file__).resolve().parent
CONFIG = HERE / "fifa-host.cfg"
WEB_FILES = HERE / ".fifa-runtime"
CONTROLLER = HERE / "controller"
XIDI = CONTROLLER / "xidi"
LOCK = json.loads((HERE / "runtime-lock.json").read_text(encoding="utf-8"))
# Leave native dgVoodoo overrides out of the game ZIP so Wine uses its own graphics libraries.
DGVOODOO_OVERRIDES = {"d3d8.dll", "ddraw.dll", "dgvoodoo.conf"}


def read_settings():
    parser = configparser.ConfigParser(interpolation=None)
    if not parser.read(CONFIG, encoding="utf-8-sig"):
        raise ValueError("Could not read fifa-host.cfg. Restore the file from the repository and set game_dir.")
    if not parser.has_section("host"):
        raise ValueError("Add the [host] section to fifa-host.cfg.")
    return parser


def configured_path(value):
    return (CONFIG.parent / Path(value).expanduser()).resolve()


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(name, url, pin):
    path = WEB_FILES / name
    if path.exists() and digest(path) == pin:
        return
    with NamedTemporaryFile(dir=WEB_FILES, delete=False) as temp:
        partial = Path(temp.name)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        if digest(partial) != pin:
            raise ValueError(f"SHA-256 mismatch for {name}: the download does not match runtime-lock.json.")
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def game_config(path):
    config = path.read_bytes()
    for name, value in [(b"VIDEO", b"0"), (b"AUDIO", b"1")]:
        pattern = rb"^([ \t]*" + name + rb"[ \t]*=[ \t]*)\d+(?=[ \t]*(?://[^\r\n]*)?\r?$)"
        config, count = re.subn(pattern, lambda match: match[1] + value, config, flags=re.M | re.I)
        if count != 1:
            raise ValueError(f"Expected exactly one {name.decode()} setting in {path}")
    return config


def pack_game(game):
    executable = game / "fifa2003.exe"
    if not executable.is_file():
        raise ValueError(f"Could not find {executable}. Set game_dir to the installed FIFA folder.")
    config = game_config(game / "soccer.ini")
    data = game / "data"
    if not data.is_dir() or not any(data.iterdir()):
        raise ValueError("Missing game data")
    overlays = {
        "dinput.dll": XIDI / "dinput.dll",
        "Xidi.32.dll": XIDI / "Xidi.32.dll",
        "xinput1_4.dll": CONTROLLER / "xinput1_4.dll",
        "Xidi.ini": CONTROLLER / "Xidi.ini",
        "Xidi-LICENSE.txt": XIDI / "LICENSE",
    }
    for notice in sorted((XIDI / "ThirdParty").iterdir()):
        overlays[f"Xidi-licenses/{notice.name}"] = notice
    excluded = DGVOODOO_OVERRIDES | {"soccer.ini"} | {name.lower() for name in overlays}
    with NamedTemporaryFile(dir=WEB_FILES, delete=False) as temp:
        partial = Path(temp.name)
    try:
        with zipfile.ZipFile(partial, "w", zipfile.ZIP_DEFLATED, compresslevel=1) as archive:
            for path in sorted(game.rglob("*")):
                relative = path.relative_to(game).as_posix()
                if relative.lower() not in excluded:
                    archive.write(path, relative)
            archive.writestr("soccer.ini", config)
            for name, path in overlays.items():
                archive.write(path, name)
        with zipfile.ZipFile(partial) as archive:
            bad = archive.testzip()
            if bad:
                raise ValueError(f"Failed CRC check for {bad}")
        # Boxedwine uses the ZIP name to look up existing browser saves.
        partial.replace(WEB_FILES / "fifa325-pad.zip")
    finally:
        partial.unlink(missing_ok=True)


def write_launcher():
    stock = (WEB_FILES / "boxedwine.html").read_text(encoding="utf-8")
    marker = "<script src=boxedwine-shell.js>"
    if stock.count(marker) != 1:
        raise ValueError("Unexpected Boxedwine launcher HTML")
    page = stock.replace(marker, '<script src="gamepad.js"></script>' + marker)
    (WEB_FILES / "fifa.html").write_text(page, encoding="utf-8")
    for name in ("index.html", "gamepad.js"):
        shutil.copyfile(HERE / name, WEB_FILES / name)


def prepare(settings):
    game_dir = settings["host"].get("game_dir", "").strip()
    if not game_dir:
        raise ValueError("Set game_dir in fifa-host.cfg to the installed FIFA folder.")
    runtime_url = settings.get("boxedwine", "runtime_url", fallback="").rstrip("/")
    filesystem_url = settings.get("boxedwine", "filesystem_url", fallback="")
    if not runtime_url or not filesystem_url:
        raise ValueError("Set runtime_url and filesystem_url in the [boxedwine] section of fifa-host.cfg.")

    game = configured_path(game_dir)
    output = WEB_FILES.resolve()
    if output.is_relative_to(game) or game.is_relative_to(output):
        raise ValueError("Choose a game directory outside the host's generated files.")

    WEB_FILES.mkdir(exist_ok=True)
    print(f"Preparing FIFA from {game}", flush=True)
    pack_game(game)
    for name, metadata in LOCK["runtime"].items():
        fetch(name, f"{runtime_url}/{name}", metadata["sha256"])
    fetch("boxedwine.zip", filesystem_url, LOCK["filesystem"]["archive"]["sha256"])
    write_launcher()


if __name__ == "__main__":
    try:
        prepare(read_settings())
    except (OSError, ValueError, configparser.Error) as error:
        raise SystemExit(str(error)) from error
