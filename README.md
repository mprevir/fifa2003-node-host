# FIFA 2003 Node host

Run FIFA Soccer 2003 in a desktop browser using a Windows host. Boxedwine runs the game on the client, and each browser plays its own match and keeps its own saves.

## Requirements

- Windows host with Node.js 24 or newer and Python 3.11 or newer.
- Caddy on the Windows host for LAN play. Install it on your PATH or use a portable executable. [Install Caddy](https://caddyserver.com/docs/install)

## TL;DR

1. Edit `fifa-host.cfg`
2. Run `python prepare.py` to download Boxedwine and package the game ahead of time
3. Run `python host.py` to prepare the game and launch the server
4. ...
5. PROFIT!!

## 1. Prepare the host files

Build 235 of FIFA Soccer 2003 for PC is recommended. Use your own installation or download and install the PC release from the Internet Archive. Use the installed folder containing `fifa2003.exe`, `soccer.ini`, and the `data` directory, including the game audio. [FIFA Soccer 2003 at the Internet Archive](https://archive.org/details/fifa2003_multi7)

Edit [fifa-host.cfg](fifa-host.cfg) in the repository. For LAN play, find the IPv4 address of the Windows network adapter using `ipconfig`.

```ini
[host]
game_dir = D:/Games/FIFA 2003
lan_ip = 192.168.20.3
caddy_path =
```

- `game_dir` is the installed game folder. Absolute paths and paths relative to the configuration file both work.
- `lan_ip` is the Windows host's IPv4 address on the same network as the client. Leave it blank to play on the host itself. Also you can use VLAN tools like Hamachi, ZeroTier, etc. to create a virtual LAN and play over the Internet
- `caddy_path` can point to a portable `caddy.exe`. Leave it blank to find Caddy on PATH.

Replace the sample values with your own. Enter the IPv4 address by itself in `lan_ip`. The server adds HTTPS and port 8443, giving `https://192.168.20.3:8443/` for this example.

To download the Boxedwine browser runtime and package the game without starting the server, open PowerShell in the repository and run this command.

```powershell
python prepare.py
```

Note: `python host.py` runs the same preparation before starting the server and reuses verified Boxedwine files from an earlier run. But better to download and install Boxedwine beforehand

## 2. Start the host

Open PowerShell in the repository and run the host.

```powershell
python host.py
```

The script packages FIFA, downloads the pinned Boxedwine runtime when needed, and starts Node. When `lan_ip` is set, it also starts Caddy and prints the HTTPS address and public certificate path. Leave the PowerShell window open while playing. Press **Ctrl+C** to stop the host.

<img width="1213" height="463" alt="image" src="https://github.com/user-attachments/assets/83792673-a7d8-4b4f-84c3-7993d3346df2" />

If the Boxedwine files at boxedwine.org move or URL changes completely - update `runtime_url` or `filesystem_url` in the `[boxedwine]` section of `fifa-host.cfg`. A mirror of the same files works with the existing [runtime-lock.json](runtime-lock.json). A different Boxedwine release needs a matching lockfile and a compatibility check.

For play on the host itself, open <http://127.0.0.1:8325/>. If you already have a FIFA host running, stop it before starting this one so the ports are available.

## 3. Setting up the client side browser

On Linux, macOS, or Windows, use a Chromium-based browser such as Chrome, Chromium, or Edge. Hardware-accelerated WebGL is recommended.

1. After the host starts, copy the public `root.crt` from the printed path to the client. Keep the CA's private keys on the host. [Caddy local HTTPS](https://caddyserver.com/docs/automatic-https#local-https)
2. Import the certificate as a trusted root on the client.

   - **Linux**. In Chrome or Chromium, open `chrome://settings/certificates` and import it as an authority trusted for websites. [Chromium certificate management on Linux](https://chromium.googlesource.com/chromium/src.git/+/refs/heads/main/docs/linux/cert_management.md)
   - **macOS**. Import it in Keychain Access and trust it for SSL.
   - **Windows**. Run `certmgr.msc` and import it under **Trusted Root Certification Authorities → Certificates** for the current user.
3. Open the HTTPS address printed by the host. The first load may take a while because the browser downloads the game package. If the connection times out, check that both devices are on the same LAN and that Windows Firewall permits inbound TCP 8443 from the client on the active profile.

## 4. Play a friendly

1. Click inside the game and press Enter at the title screen. Press a face button on your gamepad and check that its name appears above the game.
<img width="1280" height="800" alt="photo_2026-11-19_08-40-36" src="https://github.com/user-attachments/assets/e9bfd199-94ed-4e65-b15f-fd5d25eba332" />
2. Use the mouse to select **Play a Club Championship Friendly**. At **Select Sides**, use the keyboard arrows and the gamepad's left stick or D-pad to assign the two device icons. The launcher supports one browser gamepad plus the keyboard.
3. Start the match. Use the arrow keys to move, **S** to pass, **A** for a long ball, **D** to shoot, **W** to cross, and **Esc** to pause. See **Control Options** for the gamepad mappings.

<img width="1280" height="800" alt="photo_2026-11-19_08-40-58" src="https://github.com/user-attachments/assets/30929fca-af7b-4450-bda4-f6b0f37d3e17" />


If the game is choppy, check WebGL hardware acceleration at `chrome://gpu` or `edge://gpu`.



## Controller files

[gamepad.js](gamepad.js) writes the first browser pad's state to the Boxedwine memory-backed D: drive. The bundled `xinput1_4.dll` reads it and Xidi presents it to FIFA as a separate DirectInput controller. To rebuild the custom DLL, run `controller\build.cmd` from an x86 Visual Studio Developer Command Prompt and restart the host. The bundled DLLs and their notices are under [controller/xidi](controller/xidi). [Xidi upstream release](https://github.com/samuelgr/Xidi/releases/tag/v5.0.0)
