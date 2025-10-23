import os
import string
from functools import lru_cache
from typing import Dict, List

try:
    from pypinyin import lazy_pinyin, Style  # type: ignore
except ImportError:  # pragma: no cover - optional dependency
    lazy_pinyin = None
    Style = None


class CharacterLimiter:
    def __init__(self, allowed_chars_path: str):
        self.allowed_chars_path = allowed_chars_path
        self.allowed_chars = self._load_allowed_chars()
        self.base_allowed = set(string.printable)  # ASCII characters are considered safe
        self.base_allowed.update(self.allowed_chars)
        self._replacement_cache: Dict[str, str] = {}
        self._pinyin_to_chars: Dict[str, List[str]] = {}
        if lazy_pinyin is not None and Style is not None:
            self._build_pinyin_index()

    def _load_allowed_chars(self) -> List[str]:
        try:
            with open(self.allowed_chars_path, "r", encoding="utf-8") as f:
                content = f.read()
                return [ch for ch in content if ch.strip()]
        except Exception:
            return []

    def _build_pinyin_index(self) -> None:
        for ch in self.allowed_chars:
            py_keys = self._generate_pinyin_keys(ch)
            for key in py_keys:
                if not key:
                    continue
                self._pinyin_to_chars.setdefault(key, []).append(ch)

    def _generate_pinyin_keys(self, ch: str) -> List[str]:
        keys: List[str] = []
        if lazy_pinyin is None or Style is None:
            return keys
        try:
            tone_keys = lazy_pinyin(ch, style=Style.TONE3, neutral_tone_with_five=True)
            normal_keys = lazy_pinyin(ch, style=Style.NORMAL)
        except Exception:
            return keys
        for seq in (tone_keys, normal_keys):
            if not seq:
                continue
            key = seq[0]
            if key:
                keys.append(key)
        return list(dict.fromkeys(keys))  # preserve order, remove duplicates

    def normalize_text(self, text: str) -> str:
        if not text:
            return text
        return "".join(self._normalize_char(ch) for ch in text)

    def _normalize_char(self, ch: str) -> str:
        if ch in self.base_allowed:
            return ch
        if ch.isspace():
            return " "
        if ch in self._replacement_cache:
            return self._replacement_cache[ch]

        replacement = self._find_replacement(ch)
        self._replacement_cache[ch] = replacement
        return replacement
    def _find_replacement(self, ch: str) -> str:
        if lazy_pinyin is None or Style is None:
            return ch
        keys = self._generate_pinyin_keys(ch)
        for key in keys:
            candidates = self._pinyin_to_chars.get(key)
            if candidates:
                return candidates[0]
        return ch


_allowed_chars_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "2500常用字.txt")
character_limiter = CharacterLimiter(os.path.normpath(_allowed_chars_file))


@lru_cache(maxsize=2048)
def normalize_text(text: str) -> str:
    return character_limiter.normalize_text(text)
