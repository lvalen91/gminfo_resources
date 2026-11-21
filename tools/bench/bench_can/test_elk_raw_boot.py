import io
from pathlib import Path
import tempfile
import unittest

import elk_raw_boot as target


class Timeout(Exception):
    pass


class Endpoint:
    def __init__(self, replies=()):
        self.replies = iter(replies)
        self.writes = []

    def write(self, payload, timeout):
        self.writes.append(bytes(payload))
        return len(payload)

    def read(self, _size, timeout):
        return next(self.replies)


class FastbootTests(unittest.TestCase):
    def image(self, data=b'hello'):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        path = Path(directory.name) / 'image.img'
        path.write_bytes(data)
        return path

    def test_download_then_boot(self):
        out = Endpoint()
        inp = Endpoint([b'DATA00000005', b'OKAY', b'OKAY'])
        target.Fastboot(out, inp, Timeout).download_and_boot(self.image(), 5)
        self.assertEqual(out.writes, [b'download:00000005', b'hello', b'boot'])

    def test_info_is_consumed_before_okay(self):
        out = Endpoint()
        inp = Endpoint([b'INFOhello', b'OKAYversion'])
        self.assertEqual(target.Fastboot(out, inp, Timeout).command('getvar:version-bootloader'), 'version')

    def test_data_size_mismatch_rejected(self):
        out = Endpoint()
        inp = Endpoint([b'DATA00000004'])
        with self.assertRaisesRegex(target.FastbootError, 'differs'):
            target.Fastboot(out, inp, Timeout).download_and_boot(self.image(), 5)

    def test_fail_is_preserved(self):
        out = Endpoint()
        inp = Endpoint([b'FAILbad image'])
        with self.assertRaisesRegex(target.FastbootError, 'FAIL: bad image'):
            target.Fastboot(out, inp, Timeout).command('boot')

    def test_short_write_rejected(self):
        class Short(Endpoint):
            def write(self, payload, timeout):
                return len(payload) - 1
        with self.assertRaisesRegex(target.FastbootError, 'short USB write'):
            target.Fastboot(Short(), Endpoint(), Timeout).command('boot')

    def test_regular_file_and_cap(self):
        path, size = target.require_image(self.image())
        self.assertEqual(size, 5)
        with self.assertRaisesRegex(ValueError, 'regular file'):
            target.require_image(path.parent)


if __name__ == '__main__':
    unittest.main()

