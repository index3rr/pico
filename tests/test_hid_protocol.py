from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'projects' / 'usb_control'))
from hid_protocol import read_request, text_keys, validate

# Read the upstream keycode constants without importing hardware modules.
namespace = {}
source = (ROOT / 'projects/usb_control/lib/usb/device/keyboard.py').read_text()
exec('class KeyCode:' + source.split('class KeyCode:', 1)[1], namespace)
KeyCode = namespace['KeyCode']


class Stream:
    def __init__(self, data, chunk=7):
        self.data, self.chunk = data, chunk

    def recv(self, size):
        count = min(size, self.chunk)
        result, self.data = self.data[:count], self.data[count:]
        return result


class ProtocolTests(unittest.TestCase):
    def test_ascii_layout(self):
        self.assertEqual(text_keys('aA1!\n'), [(4,), (-2, 4), (30,), (-2, 30), (40,)])
        self.assertEqual(len(text_keys(''.join(chr(c) for c in range(32, 127)))), 95)

    def test_entire_batch_validated_before_execution(self):
        for bad in ({'type': 'text', 'text': 'é'}, {'type': 'key', 'keys': ['not-a-key']},
                    {'type': 'move', 'dx': 5000}, {'type': 'scroll', 'amount': True},
                    {'type': 'click', 'button': 'fourth'}):
            with self.assertRaises(ValueError):
                validate([{'type': 'text', 'text': 'valid'}, bad], KeyCode)

    def test_bounded_batches_and_aliases(self):
        self.assertEqual(validate([{'type': 'key', 'keys': ['CTRL', 'SEARCH', 'z']}], KeyCode),
                         [('keys', [[-1, -8, 29]])])
        with self.assertRaises(ValueError):
            validate([{'type': 'wait', 'ms': 2000}] * 6, KeyCode)
        with self.assertRaises(ValueError):
            validate([{'type': 'click'}] * 33, KeyCode)

    def test_partial_reads(self):
        body = b'{"actions":[]}'
        method, path, headers, received = read_request(Stream(
            b'POST /api/actions HTTP/1.1\r\nAuthorization: Bearer example\r\nContent-Length: '
            + str(len(body)).encode() + b'\r\n\r\n' + body))
        self.assertEqual((method, path, received), ('POST', '/api/actions', body))
        self.assertEqual(headers['authorization'], 'Bearer example')

    def test_malformed_and_unbounded_http(self):
        for request in (b'GET / HTTP/1.1\r\nX: a\r\nX: b\r\n\r\n',
                        b'POST / HTTP/1.1\r\nContent-Length: 99999\r\n\r\n',
                        b'POST / HTTP/1.1\r\nTransfer-Encoding: chunked\r\n\r\n',
                        b'POST / HTTP/1.1\r\nContent-Length: 3\r\n\r\na',
                        b'GET / HTTP/1.1\r\n' + b'A' * 5000):
            with self.assertRaises(ValueError):
                read_request(Stream(request))


if __name__ == '__main__':
    unittest.main()
