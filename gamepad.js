// Share one XINPUT_STATE packet with the separate Wine DirectInput controller.
(() => {
  const status = document.createElement("span");
  document.getElementById("controls").append(" ", status);
  let previous = "";
  let sequence = 0;
  let activeIndex;
  function update() {
    let pads;
    try {
      pads = Array.from(navigator.getGamepads?.() || []);
    } catch {
      pads = [];
    }
    const pad = pads[activeIndex] ?? pads.find(p => p?.connected);
    const direction = pad && [
      (pad.axes[0] < -0.4 || pad.buttons[14]?.pressed) && "←",
      (pad.axes[0] > 0.4 || pad.buttons[15]?.pressed) && "→",
      (pad.axes[1] < -0.4 || pad.buttons[12]?.pressed) && "↑",
      (pad.axes[1] > 0.4 || pad.buttons[13]?.pressed) && "↓",
    ].filter(Boolean).join("");
    const message = pad ? "Controller: " + pad.id + " " + direction
      : "Controller: press a gamepad button";
    if (status.textContent !== message) status.textContent = message;
    if (pad) activeIndex = pad.index;
    if (typeof FS === "undefined" || typeof Config === "undefined" || !Config.d_drive || !FS.analyzePath(Config.d_drive).exists) return;
    const packet = new Uint8Array(16);
    const view = new DataView(packet.buffer);
    if (pad && !document.hidden && document.hasFocus()) {
      // W3C standard layout to XINPUT_GAMEPAD button flags.
      const masks = [0x1000,0x2000,0x4000,0x8000,0x100,0x200,0,0,0x20,0x10,0x40,0x80,1,2,4,8];
      let buttons = 0;
      masks.forEach((mask, i) => { if (pad.buttons[i]?.pressed) buttons |= mask; });
      view.setUint16(4, buttons, true);
      packet[6] = Math.round((pad.buttons[6]?.value || 0) * 255);
      packet[7] = Math.round((pad.buttons[7]?.value || 0) * 255);
      for (let i = 0; i < 4; i++) {
        let axis = pad.axes[i] || 0;
        // Mirror the D-pad into the left stick for FIFA's axis-based Side Select.
        if (i === 0 && (buttons & 12)) axis = (buttons & 8 ? 1 : 0) - (buttons & 4 ? 1 : 0);
        if (i === 1 && (buttons & 3)) axis = (buttons & 2 ? 1 : 0) - (buttons & 1 ? 1 : 0);
        if (i % 2) axis = -axis;
        view.setInt16(8 + i * 2, Math.round(axis * (axis < 0 ? 32768 : 32767)), true);
      }
    }
    const signature = packet.join(",");
    if (signature === previous) return;
    view.setUint32(0, ++sequence, true);
    FS.writeFile(Config.d_drive + "/fifa-pad.bin", packet);
    previous = signature;
  }
  setInterval(update, 16);
  window.addEventListener("blur", update);
  document.addEventListener("visibilitychange", update);
})();
