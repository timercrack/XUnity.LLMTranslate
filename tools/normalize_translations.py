import os
import sys

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.normpath(os.path.join(CURRENT_DIR, '..'))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from core.character_limiter import normalize_text as limit_characters


def find_split_index(line: str) -> int:
    idx = 0
    length = len(line)
    while idx < length:
        pos = line.find('=', idx)
        if pos == -1:
            return -1
        if pos > 0 and line[pos - 1] == '\\':
            idx = pos + 1
            continue
        return pos
    return -1


def process_line(line: str) -> str:
    if not line:
        return line

    newline = ''
    if line.endswith('\r\n'):
        newline = '\r\n'
        line = line[:-2]
    elif line.endswith('\n'):
        newline = '\n'
        line = line[:-1]

    split_idx = find_split_index(line)
    if split_idx == -1:
        return line + newline

    key = line[:split_idx]
    value = line[split_idx + 1:]
    limited = limit_characters(value)
    return key + '=' + limited + newline


def process_file(path: str) -> None:
    with open(path, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    processed = [process_line(line) for line in lines]

    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(processed)


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print('Usage: normalize_translations.py <file>')
        sys.exit(1)

    target_file = sys.argv[1]
    if not os.path.isfile(target_file):
        print(f'File not found: {target_file}')
        sys.exit(1)

    process_file(target_file)
    print(f'Normalized translations in {target_file}')
