"""Single-owner arbitration for the local radio_on command."""

import contextlib
import fcntl
import json
import os
from pathlib import Path
import secrets
import signal
import socket
import stat
import subprocess
import sys
import time


def process_start(pid):
    env = dict(os.environ, LC_ALL='C', TZ='UTC')
    result = subprocess.run(
        ['/bin/ps', '-p', str(pid), '-o', 'lstart='], capture_output=True, text=True,
        env=env, timeout=2,
    )
    return result.stdout.strip() if result.returncode == 0 else None


def try_lock(fd):
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        return False
    return True


class Owner:
    def __init__(self, control, token):
        self.control = control
        self.token = token

    def poll(self):
        """Only the process holding the lease may signal itself."""
        try:
            raw, address = self.control.recvfrom(128)
        except BlockingIOError:
            return
        if not address:
            return
        if raw == b'ping ' + self.token:
            reply = b'owned ' + self.token
        elif raw == b'stop ' + self.token:
            reply = b'stopping ' + self.token
        else:
            return
        try:
            self.control.sendto(reply, address)
        except (FileNotFoundError, ConnectionRefusedError, BlockingIOError):
            return
        if reply.startswith(b'stopping '):
            os.kill(os.getpid(), signal.SIGTERM)


def request_control(directory, token, command):
    local = directory / ('c-' + secrets.token_hex(6))
    with socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM) as client:
        client.settimeout(2)
        client.bind(str(local))
        try:
            client.connect(str(directory / 'control'))
            client.send(command + b' ' + token)
            answer = client.recv(128)
        finally:
            local.unlink(missing_ok=True)
    return answer


def request_handoff(fd, directory):
    try:
        record = json.loads(os.pread(fd, 512, 0))
        pid, start = record['pid'], record['start']
        token = bytes.fromhex(record['token'])
        if (type(pid) is not int or pid <= 0 or not isinstance(start, str)
                or not start or len(token) != 16 or process_start(pid) != start):
            raise ValueError('stale owner identity')
        if request_control(directory, token, b'ping') != b'owned ' + token:
            raise ValueError('invalid owner reply')
    except (OSError, ValueError, KeyError, TypeError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f'CANable owner lock is held; unable to verify owner: {error}') from error

    label = f'radio_on PID {pid}, started {start} UTC'
    if not sys.stdin.isatty():
        raise RuntimeError(f'{label} holds the CANable owner lock. Noninteractive exit.')
    print(f'{label} holds the CANable. Request SIGTERM and wait? [y/N] ',
          end='', file=sys.stderr, flush=True)
    if sys.stdin.readline().strip().lower() not in ('y', 'yes'):
        raise RuntimeError('owner termination declined')
    # A replacement owner uses a new nonce. Never send a signal to a stored PID.
    if process_start(pid) != start:
        raise RuntimeError('owner identity changed while awaiting confirmation')
    if request_control(directory, token, b'stop') != b'stopping ' + token:
        raise RuntimeError('owner did not confirm SIGTERM')
    deadline = time.monotonic() + 5
    while time.monotonic() < deadline:
        if try_lock(fd):
            return
        time.sleep(.05)
    raise RuntimeError('owner did not release the CANable lock within 5 seconds')


@contextlib.contextmanager
def exclusive_owner(directory=None):
    if directory is None:
        directory = Path.home() / '.local/share/gminfo-bench/radio-on'
    directory.mkdir(mode=0o700, exist_ok=True)
    info = directory.lstat()
    if (not stat.S_ISDIR(info.st_mode) or info.st_uid != os.getuid()
            or info.st_mode & 0o077):
        raise RuntimeError('radio owner directory must be owned by this user with mode 0700')
    fd = os.open(directory / 'owner.lock', os.O_RDWR | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with contextlib.ExitStack() as cleanup:
        cleanup.callback(os.close, fd)
        info = os.fstat(fd)
        if (not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid()
                or info.st_mode & 0o077 or info.st_nlink != 1):
            raise RuntimeError('radio owner lock must be a private regular file')
        if not try_lock(fd):
            request_handoff(fd, directory)
        # Keep the inode stable on disk. Closing the fd releases the flock, even on a crash.
        os.ftruncate(fd, 0)
        cleanup.callback(os.ftruncate, fd, 0)
        control_path = directory / 'control'
        control_path.unlink(missing_ok=True)
        control = cleanup.enter_context(socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM))
        control.bind(str(control_path))
        cleanup.callback(control_path.unlink, missing_ok=True)
        os.chmod(control_path, 0o600)
        control.setblocking(False)
        pid = os.getpid()
        start = process_start(pid)
        if not start:
            raise RuntimeError('unable to read process start time')
        token = secrets.token_bytes(16)
        record = json.dumps(dict(pid=pid, start=start, token=token.hex())).encode()
        if os.pwrite(fd, record, 0) != len(record):
            raise OSError('short write to CANable owner lock')
        yield Owner(control, token)

