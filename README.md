# FIFA 2003 Node host

Serve FIFA Soccer 2003 Build 325 from a Windows PC and play in a desktop browser. Boxedwine runs the game on the client. The host serves the game package, so each browser plays its own match and stores its saves in that browser profile.

## Requirements

- Windows host with Node.js 24 or newer and Python 3.11 or newer. Python prepares the game package. The Node server uses built-in modules.
- A complete FIFA Soccer 2003 PC installation with `fifa2003.exe`, `soccer.ini`, and the `data` directory, including the audio files. Supply your own copy or obtain the disc images from the archive listing and install the game first. Keep the installation and generated game archive local. [FIFA Soccer 2003 at the Internet Archive](https://archive.org/details/fifa2003_multi7)
- Chrome, Chromium, or Edge on a desktop with hardware-accelerated WebGL. The LAN setup also uses Caddy on the host. The tested version was Caddy 2.11.9. [Install Caddy](https://caddyserver.com/docs/install)

## 1. Prepare the host files

Open PowerShell in this repository. Set the path to the installed game folder and check the executable before preparing it.

```powershell
$fifaGameDir = 'D:\Games\FIFA 2003'
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $fifaGameDir 'fifa2003.exe')
python prepare.py --game-dir $fifaGameDir
```

The supported executable has SHA-256 `dff7f9ae1c6ebe6a73f90013e06ebca8453daa101587a9b7bb7bf51aa2149889`. Compatibility was checked against a local full Build 325 installation. Use the hash to check an installation from other media. If you place the installed files under the repository's ignored `playtest/` directory, run `python prepare.py` with no arguments.

Preparation downloads and verifies the Boxedwine browser runtime and Wine filesystem using [runtime-lock.json](runtime-lock.json). It creates `stage/fifa325-pad.zip` with the bundled 32-bit controller DLLs and `VIDEO = 0` and `AUDIO = 1` in the packaged `soccer.ini`. The input installation stays intact. Keep `stage/` outside version control.

### Restore an existing playtested stage

If you already have the known-good stage, you can copy its launcher and runtime files into this checkout's `stage/` and start at step 2. From the migrated clone inside the original `web-port` folder, the original stage is at `..\stage`.

```powershell
$previousStage = '..\stage'
$stageFiles = @(
    'index.html', 'fifa.html', 'gamepad.js',
    'boxedwine.html', 'boxedwine.css', 'boxedwine-shell.js', 'boxedwine.js',
    'boxedwine.wasm', 'boxedwine.zip', 'fifa325-pad.zip'
)
New-Item -ItemType Directory -Path .\stage -Force | Out-Null
foreach ($name in $stageFiles) {
    Copy-Item -LiteralPath (Join-Path $previousStage $name) -Destination .\stage
}
Get-FileHash -Algorithm SHA256 -LiteralPath .\stage\fifa325-pad.zip
```

The exact playtested game archive has SHA-256 `7d6716fba7c19f4d85875dcc6a323e15ec139c00bddc861780c310038d156b7c`. A rebuild can produce a different ZIP hash because file timestamps and compression can vary.

## 2. Start Node and check the launcher

If you are migrating an existing host, stop the old Node and Caddy instances before starting them from this checkout so the ports are available.

```powershell
node server.mjs
```

Open <http://127.0.0.1:8325/> on Windows. The server listens on loopback and serves `stage/` by default. To use a different prepared stage, pass `--root` with its directory. The launcher can take a while on the first load. The game ZIP alone is about 1 GB.

## 3. Make the launcher available on the LAN

1. Run `ipconfig` and find the IPv4 address of the Windows adapter on the same network as the client.
2. Leave Node running. Open a second PowerShell in this repository and run the commands below. Replace the example IP with the Windows LAN IP. If using a portable Caddy executable placed at `tools/caddy.exe`, use `.\tools\caddy.exe` in place of `caddy`.

   ```powershell
   $env:FIFA_LAN_IP = '192.168.1.50'
   caddy environ | Select-String '^caddy.AppDataDir='
   caddy validate --config .\Caddyfile --adapter caddyfile
   caddy run --config .\Caddyfile --adapter caddyfile
   ```

3. From the printed `caddy.AppDataDir`, copy the public `pki/authorities/local/root.crt` file to the client after Caddy starts. On Ubuntu, open `chrome://settings/certificates` and import it as an authority trusted for websites. On macOS, import it in Keychain Access and trust it for SSL. Keep the CA keys on the host. Reuse the same Caddy data directory on restarts to retain the CA that your client already trusts. [Caddy local HTTPS](https://caddyserver.com/docs/automatic-https#local-https) · [Chromium certificate management on Linux](https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/linux/cert_management.md)
4. Open `https://192.168.1.50:8443/` on the client, replacing the IP with the same value used above. If it times out, check that both devices are on the same LAN and that Windows Firewall permits inbound TCP 8443 on the active profile. Scope any firewall rule to the test client or trusted LAN.

The client should accept the certificate without a warning. For a browser check, open DevTools after the launcher loads and confirm `window.isSecureContext` and `window.crossOriginIsolated` are both `true`. The launcher, Wasm, and ZIP requests should succeed in the Network panel.

## 4. Play a friendly

1. Click inside the game and press Enter at the title screen. Press a face button on the controller and check that its name appears above the game.
2. Use the mouse to select **Play a Club Championship Friendly** and proceed to **Select Sides**. Use the keyboard arrows and the gamepad's left stick or D-pad to assign the two separate device icons. The launcher supports one browser gamepad plus the keyboard.
3. Start the friendly and check that you can move, pass, shoot, pause, and hear the game's audio. Keyboard controls are arrows to move, **S** to pass, **A** for a long ball, **D** to shoot, **W** to cross, and **Esc** to pause. See **Control Options** for the pad's mappings.

A full friendly was completed from Ubuntu Chrome over LAN HTTPS in the original setup. If the game is choppy, check WebGL hardware acceleration at `chrome://gpu` or `edge://gpu`.

## Controller files

[gamepad.js](gamepad.js) writes the first browser pad's state to the Boxedwine memory-backed D: drive. The bundled `xinput1_4.dll` reads it and Xidi presents it to FIFA as a separate DirectInput controller. To rebuild the custom DLL, run `controller\build.cmd` from an x86 Visual Studio Developer Command Prompt, then run preparation again. The bundled Xidi 5.0.0 DLLs and their notices are under [controller/xidi](controller/xidi). [Xidi upstream release](https://github.com/samuelgr/Xidi/releases/tag/v5.0.0)
