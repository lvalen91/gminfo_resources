"use strict";
/* Client-side-only log capture + .tar export.
 *
 * Purpose: avoid Pi SD-card wear. The backend already never writes continuous
 * console/terminal logs to disk (uart.py is pure in-memory fanout, terminals.py's
 * os.write calls are interactive PTY I/O, not log files) -- this module adds the
 * browser-side half the owner asked for: an in-memory scrollback of what the
 * dashboard is already displaying (UART console, CAN monitor, terminal output),
 * kept entirely in this tab's JS heap, plus a button to bundle it into a real
 * .tar file and save it via a normal browser download. Nothing here ever touches
 * the Pi's filesystem or makes a server round-trip.
 */

const LogCapture = (() => {
  // Cap per stream: 4 MiB of raw text. That's tens of thousands of UART/CAN lines --
  // enough to hold a full bench debugging session's scrollback -- while bounding how
  // much memory a tab can accumulate if left open and streaming for hours unattended.
  // Exceeding the cap drops the OLDEST captured text first (a ring buffer), so the
  // export always reflects the most recent activity.
  const CAP_BYTES = 4 * 1024 * 1024;
  const streams = new Map(); // id -> { chunks: string[], bytes: number, label: string }

  function _get(id, label) {
    let s = streams.get(id);
    if (!s) { s = { chunks: [], bytes: 0, label: label || id }; streams.set(id, s); }
    else if (label) s.label = label;
    return s;
  }

  // Register (or re-fetch) a named capture stream. Safe to call more than once for
  // the same id (e.g. re-opening a terminal) -- it reuses the existing buffer rather
  // than resetting it, so switching UART ports or reconnecting a shell doesn't lose
  // earlier captured output.
  function register(id, label) {
    _get(id, label);
    return {
      push(text) {
        if (!text) return;
        const s = streams.get(id);
        s.chunks.push(text);
        s.bytes += text.length;
        while (s.bytes > CAP_BYTES && s.chunks.length > 1) {
          s.bytes -= s.chunks.shift().length;
        }
      },
      clear() {
        const s = streams.get(id);
        s.chunks = []; s.bytes = 0;
      },
    };
  }

  // {id: fullText} for every stream that has captured at least one byte.
  function snapshot() {
    const out = {};
    for (const [id, s] of streams) {
      if (s.bytes > 0) out[id] = s.chunks.join("");
    }
    return out;
  }

  return { register, snapshot };
})();

/* ---------------- minimal from-scratch USTAR (tar) writer ----------------
 * No third-party JS dependency: a USTAR archive is just 512-byte header blocks
 * (name/mode/size/mtime/checksum, etc.) followed by the file content padded to a
 * 512-byte boundary, terminated by two 512-byte zero blocks. Uncompressed -- gzip
 * would need a from-scratch DEFLATE implementation to stay dependency-free, which
 * isn't trivial, so plain .tar is what this writes. */
function _tarOctalField(value, length) {
  // `length` total bytes: (length-1) left-zero-padded octal digits + a NUL terminator.
  const digits = length - 1;
  let s = Math.max(0, Math.floor(value)).toString(8);
  if (s.length > digits) s = s.slice(-digits);
  s = s.padStart(digits, "0");
  const out = new Uint8Array(length);
  out.set(new TextEncoder().encode(s));
  return out; // trailing byte(s) already 0 (NUL) from the typed-array init
}
function _tarChecksumField(sum) {
  // USTAR checksum field: 6 octal digits, NUL, space.
  const out = new Uint8Array(8);
  out.set(new TextEncoder().encode(sum.toString(8).padStart(6, "0")));
  out[7] = 0x20;
  return out;
}
function _tarStrField(str, length) {
  const out = new Uint8Array(length); // zero-filled -> NUL-padded ASCII field
  out.set(new TextEncoder().encode(str).subarray(0, length));
  return out;
}
function _tarHeader(name, size, mtimeSec) {
  const BLOCK = 512;
  const h = new Uint8Array(BLOCK);
  h.set(_tarStrField(name, 100), 0);          // name
  h.set(_tarOctalField(0o644, 8), 100);       // mode
  h.set(_tarOctalField(0, 8), 108);           // uid
  h.set(_tarOctalField(0, 8), 116);           // gid
  h.set(_tarOctalField(size, 12), 124);       // size
  h.set(_tarOctalField(mtimeSec, 12), 136);   // mtime
  h.fill(0x20, 148, 156);                      // checksum placeholder: 8 spaces
  h[156] = "0".charCodeAt(0);                  // typeflag: regular file
  h.set(_tarStrField("ustar", 6), 257);        // magic
  h.set(_tarStrField("00", 2), 263);           // version
  let sum = 0;
  for (let i = 0; i < BLOCK; i++) sum += h[i];
  h.set(_tarChecksumField(sum), 148);
  return h;
}
// files: [{name, data, mtime?}], data a string (encoded as UTF-8) or Uint8Array.
function makeTar(files) {
  const BLOCK = 512;
  const enc = new TextEncoder();
  const blocks = [];
  for (const f of files) {
    const data = typeof f.data === "string" ? enc.encode(f.data) : f.data;
    blocks.push(_tarHeader(f.name, data.length, Math.floor((f.mtime || Date.now()) / 1000)));
    blocks.push(data);
    const rem = data.length % BLOCK;
    if (rem !== 0) blocks.push(new Uint8Array(BLOCK - rem));
  }
  blocks.push(new Uint8Array(BLOCK * 2)); // end-of-archive: two zero blocks
  const total = blocks.reduce((n, b) => n + b.length, 0);
  const out = new Uint8Array(total);
  let off = 0;
  for (const b of blocks) { out.set(b, off); off += b.length; }
  return out;
}

// Generic client-side download trigger: Blob + object URL + synthetic <a download>.
// Saves to the viewing browser/workstation's own downloads location -- there is no
// cross-browser API to pick an arbitrary OS temp directory, so this is the correct
// implementation of "export to the browser/workstation" with no server round-trip.
function downloadBlob(filename, blob) {
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url; a.download = filename; a.style.display = "none";
  document.body.appendChild(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 2000);
}

function exportCapturedLogsAsTar() {
  const snap = LogCapture.snapshot();
  const ids = Object.keys(snap);
  if (!ids.length) {
    alert("Nothing captured yet -- open a UART/CAN/terminal view first, then export.");
    return;
  }
  const files = ids.map((id) => ({ name: id + ".log", data: snap[id] }));
  const tarBytes = makeTar(files);
  const stamp = new Date().toISOString().replace(/[:.]/g, "-");
  downloadBlob(`bench-logs-${stamp}.tar`, new Blob([tarBytes], { type: "application/x-tar" }));
}
