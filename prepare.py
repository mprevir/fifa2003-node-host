"""Stage the local Build 325 installation for Boxedwine (Python 3.11+)."""
import argparse
import hashlib
import json
import re
import shutil
import urllib.request
import zipfile
from pathlib import Path
from tempfile import NamedTemporaryFile

HERE = Path(__file__).resolve().parent
STAGE = HERE / "stage"
CONTROLLER = HERE / "controller"
XIDI = CONTROLLER / "xidi"
LOCK = json.loads((HERE / "runtime-lock.json").read_text(encoding="utf-8"))
BUILD = "https://boxedwine.org/builds/demos/build/master/138/st-jit/"
EXE_HASH = "dff7f9ae1c6ebe6a73f90013e06ebca8453daa101587a9b7bb7bf51aa2149889"
EXCLUDE = {"d3d8.dll", "ddraw.dll", "dgvoodoo.conf"}


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def fetch(name, url, pin):
    path = STAGE / name
    if path.exists() and digest(path) == pin:
        return
    with NamedTemporaryFile(dir=STAGE, delete=False) as temp:
        partial = Path(temp.name)
    try:
        with urllib.request.urlopen(url, timeout=120) as response, partial.open("wb") as output:
            shutil.copyfileobj(response, output)
        if digest(partial) != pin:
            raise ValueError(f"SHA-256 mismatch for {name}")
        partial.replace(path)
    finally:
        partial.unlink(missing_ok=True)


def game_config(path):
    config = path.read_bytes()
    for name, value in [(b"VIDEO", b"0"), (b"AUDIO", b"1")]:
        pattern = rb"^(" + name + rb"[ \t]*=[ \t]*)\d+(?=[ \t]*\r?$)"
        config, count = re.subn(pattern, lambda match: match[1] + value, config, flags=re.M | re.I)
        if count != 1:
            raise ValueError(f"Expected exactly one {name.decode()} setting in {path}")
    return config


def pack_game(game):
    executable = game / "fifa2003.exe"
    if not executable.is_file() or digest(executable) != EXE_HASH:
        raise ValueError(f"Expected the supported Build 325 executable at {executable}")
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
    excluded = EXCLUDE | {"soccer.ini"} | {name.lower() for name in overlays}
    with NamedTemporaryFile(dir=STAGE, delete=False) as temp:
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
        partial.replace(STAGE / "fifa325-pad.zip")
        print("fifa325-pad.zip SHA-256", digest(STAGE / "fifa325-pad.zip"))
    finally:
        partial.unlink(missing_ok=True)


def stage_launcher():
    stock = (STAGE / "boxedwine.html").read_text(encoding="utf-8")
    marker = "<script src=boxedwine-shell.js>"
    if stock.count(marker) != 1:
        raise ValueError("Unexpected Boxedwine launcher HTML")
    page = stock.replace(marker, '<script src="gamepad.js"></script>' + marker)
    (STAGE / "fifa.html").write_text(page, encoding="utf-8")
    for name in ("index.html", "gamepad.js"):
        shutil.copyfile(HERE / name, STAGE / name)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--game-dir", type=Path, default=HERE / "playtest",
                        help="Build 325 installation directory (default: local playtest/)")
    game = parser.parse_args().game_dir.resolve()
    if STAGE.resolve().is_relative_to(game):
        parser.error("the stage directory must be outside the input game directory")

    STAGE.mkdir(exist_ok=True)
    pack_game(game)
    for name, metadata in LOCK["runtime"].items():
        fetch(name, BUILD + name, metadata["sha256"])
    fetch("boxedwine.zip", "https://boxedwine.org/v2/41/TinyCore15Wine11.0-web.zip",
          LOCK["filesystem"]["archive"]["sha256"])
    stage_launcher()


if __name__ == "__main__":
    main()
