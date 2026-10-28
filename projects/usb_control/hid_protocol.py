"""Validate complete commands before emitting any input. Also runs on CPython."""
ALIASES = {
    'CTRL': 'LEFT_CTRL', 'CONTROL': 'LEFT_CTRL', 'SHIFT': 'LEFT_SHIFT',
    'ALT': 'LEFT_ALT', 'GUI': 'LEFT_UI', 'SUPER': 'LEFT_UI',
    'SEARCH': 'LEFT_UI', 'LAUNCHER': 'LEFT_UI', 'ESC': 'ESCAPE',
    'RETURN': 'ENTER', 'PERIOD': 'DOT',
}


def text_keys(text):
    """US keyboard layout. Each tuple is one press, followed by a release."""
    if not isinstance(text, str) or len(text) > 512:
        raise ValueError('text must be a string of at most 512 characters')
    result = []
    plain = "1234567890-=[]\\;'`,./"
    shifted = '!@#$%^&*()_+{}|:"~<>?'
    codes = [30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 45, 46, 47, 48, 49, 51, 52, 53, 54, 55, 56]
    for char in text:
        if 'a' <= char <= 'z':
            keys = (ord(char) - ord('a') + 4,)
        elif 'A' <= char <= 'Z':
            keys = (-2, ord(char) - ord('A') + 4)
        elif char in plain:
            keys = (codes[plain.index(char)],)
        elif char in shifted:
            keys = (-2, codes[shifted.index(char)])
        elif char in (' ', '\n', '\t'):
            keys = ({' ': 44, '\n': 40, '\t': 43}[char],)
        else:
            raise ValueError('Unsupported character; typing currently uses US ASCII layout')
        result.append(keys)
    return result


def integer(value, low, high, name):
    if type(value) is not int or not low <= value <= high:
        raise ValueError('%s must be an integer from %d to %d' % (name, low, high))
    return value


def validate(actions, keycodes):
    if not isinstance(actions, list) or not 1 <= len(actions) <= 32:
        raise ValueError('actions must contain 1 to 32 commands')
    prepared = []
    total_ms = 0
    for action in actions:
        if not isinstance(action, dict):
            raise ValueError('Each action must be an object')
        kind = action.get('type')
        if kind == 'text':
            sequence = text_keys(action.get('text'))
            total_ms += len(sequence) * 40
            prepared.append(('keys', sequence))
        elif kind == 'key':
            names = action.get('keys')
            if not isinstance(names, list) or not 1 <= len(names) <= 6:
                raise ValueError('keys must contain 1 to 6 key names')
            keys = []
            for name in names:
                if not isinstance(name, str):
                    raise ValueError('Key names must be strings')
                name = ALIASES.get(name.upper(), name.upper())
                code = getattr(keycodes, name, None)
                if type(code) is not int:
                    raise ValueError('Unknown key: %s' % name)
                keys.append(code)
            prepared.append(('keys', [keys]))
            total_ms += 40
        elif kind == 'move':
            dx = integer(action.get('dx', 0), -2048, 2048, 'dx')
            dy = integer(action.get('dy', 0), -2048, 2048, 'dy')
            prepared.append(('move', dx, dy))
        elif kind == 'click':
            button = action.get('button', 'left')
            if button not in ('left', 'right', 'middle'):
                raise ValueError('button must be left, right, or middle')
            prepared.append(('click', {'left': 1, 'right': 2, 'middle': 4}[button]))
            total_ms += 40
        elif kind == 'scroll':
            prepared.append(('scroll', integer(action.get('amount'), -127, 127, 'amount')))
        elif kind == 'wait':
            duration = integer(action.get('ms'), 0, 2000, 'ms')
            prepared.append(('wait', duration))
            total_ms += duration
        else:
            raise ValueError('Unknown action type')
    if total_ms > 10000:
        raise ValueError('Batch too long; split it into commands shorter than 10 seconds')
    return prepared


def read_request(client):
    """Bounded HTTP/1.1 parser, no transfer encoding or pipelining."""
    data = b''
    while b'\r\n\r\n' not in data:
        chunk = client.recv(512)
        if not chunk:
            raise ValueError('Incomplete HTTP headers')
        data += chunk
        if len(data) > 4096:
            raise ValueError('Headers too large')
    head, body = data.split(b'\r\n\r\n', 1)
    lines = head.decode().split('\r\n')
    method, path, version = lines[0].split(' ')
    if version not in ('HTTP/1.0', 'HTTP/1.1'):
        raise ValueError('Unsupported HTTP version')
    headers = {}
    for line in lines[1:]:
        key, value = line.split(':', 1)
        key = key.strip().lower()
        if key in headers:
            raise ValueError('Duplicate HTTP header')
        headers[key] = value.strip()
    if 'transfer-encoding' in headers:
        raise ValueError('Transfer encoding is unsupported')
    length = int(headers.get('content-length', '0'))
    if not 0 <= length <= 8192:
        raise ValueError('Body too large')
    while len(body) < length:
        chunk = client.recv(min(1024, length - len(body)))
        if not chunk:
            raise ValueError('Incomplete HTTP body')
        body += chunk
    return method, path, headers, body[:length]
