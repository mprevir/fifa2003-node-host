"""Prepare and serve FIFA on the Windows host."""
import configparser
import os
import shutil
import subprocess
import time
from contextlib import ExitStack
from ipaddress import IPv4Address
from pathlib import Path

from prepare import HERE, configured_path, prepare, read_settings


def executable(name, path=""):
    command = str(configured_path(path)) if path else name
    found = shutil.which(command)
    if not found:
        raise ValueError(f"Could not find {command}. Install {name} before starting the host.")
    return found


def certificate_path(caddy, env):
    result = subprocess.run([caddy, "environ"], env=env, capture_output=True, check=True)
    for line in result.stdout.decode("utf-8", errors="replace").splitlines():
        name, _, value = line.partition("=")
        if name == "caddy.AppDataDir":
            return Path(value) / "pki" / "authorities" / "local" / "root.crt"
    raise ValueError("Caddy did not report its data directory.")


def stop(process):
    if process.poll() is None:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait()


def main():
    settings = read_settings()
    node = executable("node")
    lan_ip = settings.get("lan_ip", "").strip()
    if lan_ip:
        try:
            address = IPv4Address(lan_ip)
        except ValueError as error:
            raise ValueError("Set lan_ip in fifa-host.cfg to the host's LAN IPv4 address.") from error
        if address.is_unspecified or address.is_multicast:
            raise ValueError("Set lan_ip in fifa-host.cfg to a specific interface address.")
        caddy = executable("caddy", settings.get("caddy_path", "").strip())
        env = {**os.environ, "FIFA_LAN_IP": str(address)}
        certificate = certificate_path(caddy, env)

    prepare(settings)
    with ExitStack() as processes:
        origin = subprocess.Popen([node, "server.mjs"], cwd=HERE)
        processes.callback(stop, origin)
        services = {"Node": origin}
        if lan_ip:
            proxy = subprocess.Popen([caddy, "run", "--config", "Caddyfile", "--adapter", "caddyfile"],
                                     cwd=HERE, env=env)
            processes.callback(stop, proxy)
            services["Caddy"] = proxy
            print(f"LAN launcher: https://{address}:8443/", flush=True)
            print(f"Public CA certificate (available after Caddy starts): {certificate}", flush=True)
        else:
            print("Local launcher: http://127.0.0.1:8325/", flush=True)

        while True:
            for name, process in services.items():
                status = process.poll()
                if status is not None:
                    raise RuntimeError(f"{name} stopped (exit code {status}). See its output above.")
            time.sleep(0.25)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        pass
    except (OSError, ValueError, RuntimeError, configparser.Error, subprocess.CalledProcessError) as error:
        raise SystemExit(str(error)) from error
