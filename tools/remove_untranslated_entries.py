"""移除机翻文件中未实际翻译的条目"""

import argparse
from pathlib import Path
from typing import Tuple


def _line_is_untranslated(line: str) -> bool:
    equals_index = line.find("=")
    if equals_index == -1:
        return False

    source = line[:equals_index].strip()
    target = line[equals_index + 1 :].strip()
    if source == "" or source != target:
        return False

    if len(source) <= 3:
        return False

    return True


def _process_file(path: Path) -> Tuple[int, int]:
    with path.open("r", encoding="utf-8-sig") as handler:
        lines = handler.readlines()

    kept_lines = []
    removed = 0
    for line in lines:
        if _line_is_untranslated(line):
            removed += 1
            continue
        kept_lines.append(line)

    with path.open("w", encoding="utf-8-sig", newline="") as handler:
        handler.writelines(kept_lines)

    return len(lines), removed


def main() -> None:
    parser = argparse.ArgumentParser(description="删除未翻译成功的行 (= 两侧内容完全一致)")
    parser.add_argument("file", type=Path, help="目标翻译文件路径")
    args = parser.parse_args()

    target = args.file
    if not target.exists():
        raise FileNotFoundError(f"找不到指定文件: {target}")

    total, removed = _process_file(target)
    kept = total - removed
    print(f"处理完成: 原始 {total} 行, 删除 {removed} 行, 保留 {kept} 行")


if __name__ == "__main__":
    main()
