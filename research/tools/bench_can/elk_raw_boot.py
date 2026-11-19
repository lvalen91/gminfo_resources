#!/usr/bin/env python3
"""Volatile-boot one image through the ELK raw-USB fastboot interface.

This tool deliberately implements only read-only getvar, download, and boot.
It has no flash, erase, unlock, reboot, or arbitrary-command interface.
"""

import argparse
import contextlib
import hashlib
import os
from pathlib import Path
import stat
import sys


VID = 0x8087
PID = 0x09EF
INTERFACE = (0xFF, 0x42, 0x03)
DEFAULT_MAX_DOWNLOAD = 0x08000000
CHUNK_SIZE = 1024 * 1024
TIMEOUT_MS = 10_000


class FastbootError(RuntimeError):
    pass


def require_image(value):
    path = Path(value).expanduser().resolve()
    info = path.stat()
    if not stat.S_ISREG(info.st_mode):
        raise ValueError('image must be a regular file')
    if not info.st_size:
        raise ValueError('image is empty')
    if info.st_size > DEFAULT_MAX_DOWNLOAD:
        raise ValueError(f'image exceeds conservative {DEFAULT_MAX_DOWNLOAD:#x}-byte limit')
    return path, info.st_size


def sha256(path):
    digest = hashlib.sha256()
    with path.open('rb') as image:
        for block in iter(lambda: image.read(CHUNK_SIZE), b''):
            digest.update(block)
    return digest.hexdigest()


class Fastboot:
    def __init__(self, out_endpoint, in_endpoint, timeout_error):
        self.out = out_endpoint
        self.inp = in_endpoint
        self.timeout_error = timeout_error

    def _reply(self):
        try:
            # ELK does not clear its reply buffer: the status is NUL-terminated and
            # may be followed by stale bytes from an earlier reply. Cut at the first NUL.
            raw = bytes(self.inp.read(4096, timeout=TIMEOUT_MS)).split(b'\0', 1)[0]
        except self.timeout_error as error:
            raise FastbootError('timed out waiting for ELK fastboot reply') from error
        try:
            text = raw.decode('ascii')
        except UnicodeDecodeError as error:
            raise FastbootError('ELK fastboot returned non-ASCII status') from error
        if len(text) < 4:
            raise FastbootError(f'short ELK fastboot status: {text!r}')
        return text[:4], text[4:]

    def _write(self, payload):
        written = self.out.write(payload, timeout=TIMEOUT_MS)
        if written != len(payload):
            raise FastbootError(f'short USB write: {written}/{len(payload)} bytes')

    def _status(self, allow_data=False):
        while True:
            code, payload = self._reply()
            if code == 'INFO':
                print(f'ELK INFO: {payload}', flush=True)
                continue
            if code == 'FAIL':
                raise FastbootError(f'ELK fastboot FAIL: {payload}')
            if code == 'OKAY':
                return code, payload
            if code == 'DATA' and allow_data:
                return code, payload
            raise FastbootError(f'unexpected ELK fastboot status: {code}{payload}')

    def command(self, command):
        self._write(command.encode('ascii'))
        _, payload = self._status()
        return payload

    def download_and_boot(self, image, size):
        stage = 'during download-command: '
        try:
            self._write(f'download:{size:08x}'.encode('ascii'))
            code, payload = self._status(allow_data=True)
            if code != 'DATA':
                raise FastbootError('ELK accepted download without a DATA reply')
            try:
                accepted = int(payload, 16)
            except ValueError as error:
                raise FastbootError(f'invalid ELK DATA length: {payload!r}') from error
            if accepted != size:
                raise FastbootError(f'ELK DATA length {accepted:#x} differs from image {size:#x}')
            stage = 'after image upload (finalize): '
            sent = 0
            with image.open('rb') as source:
                for block in iter(lambda: source.read(CHUNK_SIZE), b''):
                    self._write(block)
                    sent += len(block)
            if sent != size:
                raise FastbootError(f'image changed during read: sent {sent}, expected {size}')
            print(f'ELK: image upload complete ({sent} bytes sent)', flush=True)
            self._status()
            stage = 'during boot command: '
            self.command('boot')
        except FastbootError as error:
            raise FastbootError(f'{stage}{error}') from error


@contextlib.contextmanager
def elk_fastboot():
    try:
        import libusb_package
        import usb.backend.libusb1
        import usb.core
        import usb.util
    except ImportError as error:
        raise FastbootError('missing PyUSB/libusb dependency; use the bench virtual environment') from error
    backend = usb.backend.libusb1.get_backend(find_library=libusb_package.find_library)
    if backend is None:
        raise FastbootError('libusb backend unavailable')
    matches = []
    for device in usb.core.find(find_all=True, idVendor=VID, idProduct=PID, backend=backend):
        for config in device:
            for interface in config:
                if (interface.bInterfaceClass, interface.bInterfaceSubClass,
                        interface.bInterfaceProtocol) == INTERFACE:
                    matches.append((device, interface))
    if len(matches) != 1:
        raise FastbootError(f'expected exactly one ELK FF/42/03 interface; found {len(matches)}')
    device, interface = matches[0]
    out_endpoint = next((endpoint for endpoint in interface
                         if not endpoint.bEndpointAddress & 0x80), None)
    in_endpoint = next((endpoint for endpoint in interface
                        if endpoint.bEndpointAddress & 0x80), None)
    if out_endpoint is None or in_endpoint is None:
        raise FastbootError('ELK interface lacks bulk IN/OUT endpoints')
    claimed = False
    try:
        usb.util.claim_interface(device, interface.bInterfaceNumber)
        claimed = True
        yield Fastboot(out_endpoint, in_endpoint, usb.core.USBTimeoutError)
    finally:
        if claimed:
            usb.util.release_interface(device, interface.bInterfaceNumber)
        usb.util.dispose_resources(device)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('image', nargs='?', help='regular image file to RAM-download and boot')
    parser.add_argument('--probe', action='store_true', help='read ELK version and max download size only')
    parser.add_argument('--dry-run', action='store_true', help='hash and validate image only; do not open USB')
    args = parser.parse_args(argv)
    if args.probe and args.image:
        parser.error('--probe does not accept an image')
    if not args.probe and not args.image:
        parser.error('IMAGE is required unless --probe is used')
    try:
        if args.probe:
            with elk_fastboot() as fastboot:
                print('ELK version: ' + fastboot.command('getvar:version-bootloader'))
                print('ELK max-download-size: ' + fastboot.command('getvar:max-download-size'))
            return 0
        image, size = require_image(args.image)
        digest = sha256(image)
        print(f'Image {image.name}: {size} bytes SHA-256 {digest}')
        if args.dry_run:
            print('Dry run complete. USB unopened; no image sent.')
            return 0
        with elk_fastboot() as fastboot:
            maximum = int(fastboot.command('getvar:max-download-size'), 0)
            if size > maximum:
                raise FastbootError(f'image {size:#x} exceeds ELK max-download-size {maximum:#x}')
            print(f'RAM-downloading {image.name}; no persistent storage will be modified.', flush=True)
            fastboot.download_and_boot(image, size)
        print('ELK returned OKAY for download and boot. This confirms protocol acceptance, not OS boot success.')
        return 0
    except (FastbootError, OSError, ValueError) as error:
        print(f'{type(error).__name__}: {error}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())

