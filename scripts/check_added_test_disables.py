"""Fail-closed test-disable guard shared by local Git hooks and PR CI."""
from __future__ import annotations

import argparse
import io
import re
import subprocess
import sys
import tokenize
from pathlib import Path


def _blank(match: re.Match) -> str:
    return re.sub(r"[^\n]", " ", match.group())


def _python_code(source: str) -> str:
    lines = source.splitlines(keepends=True)
    offsets = [0]
    for line in lines:
        offsets.append(offsets[-1] + len(line))
    chars = list(source)
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.type not in (tokenize.STRING, tokenize.COMMENT):
            continue
        start = offsets[token.start[0] - 1] + token.start[1]
        end = offsets[token.end[0] - 1] + token.end[1]
        chars[start:end] = ["\n" if c == "\n" else " " for c in chars[start:end]]
    return "".join(chars)


def _rust_code(source: str) -> str:
    """Mask Rust literals and nested comments without consuming attributes."""
    chars = list(source)
    size = len(source)
    pos = 0
    raw_start = re.compile(r'(?:br|cr|r)(#*)"')
    character = re.compile(r"'(?:\\(?:u\{[0-9A-Fa-f_]+\}|x[0-9A-Fa-f]{2}|[^\n])|[^'\\\n])'")

    def mask(start: int, end: int) -> None:
        for index in range(start, end):
            if chars[index] != "\n":
                chars[index] = " "

    while pos < size:
        start = pos
        if source.startswith("//", pos):
            end = source.find("\n", pos)
            pos = size if end < 0 else end
        elif source.startswith("/*", pos):
            depth = 1
            pos += 2
            while pos < size and depth:
                if source.startswith("/*", pos):
                    depth += 1
                    pos += 2
                elif source.startswith("*/", pos):
                    depth -= 1
                    pos += 2
                else:
                    pos += 1
            if depth:
                raise ValueError("unterminated Rust comment")
        elif (pos == 0 or not (source[pos - 1].isalnum() or source[pos - 1] == "_")) and (raw := raw_start.match(source, pos)):
            terminator = '"' + raw.group(1)
            end = source.find(terminator, raw.end())
            if end < 0:
                raise ValueError("unterminated Rust raw string")
            pos = end + len(terminator)
        elif source[pos] == '"':
            pos += 1
            while pos < size:
                if source[pos] == "\\":
                    pos += 2
                elif source[pos] == '"':
                    pos += 1
                    break
                else:
                    pos += 1
            else:
                raise ValueError("unterminated Rust string")
        elif source[pos] == "'" and (char := character.match(source, pos)):
            pos = char.end()
        else:
            pos += 1
            continue
        mask(start, pos)
    return "".join(chars)


def _javascript_code(source: str) -> str:
    """Mask literal text while retaining executable template interpolations."""
    chars = list(source)
    size = len(source)

    def mask(start: int, end: int) -> None:
        for pos in range(start, end):
            if chars[pos] != "\n":
                chars[pos] = " "

    def quoted(start: int) -> int:
        quote = source[start]
        pos = start + 1
        while pos < size:
            if source[pos] == "\\":
                pos += 2
            elif source[pos] == quote:
                mask(start, pos + 1)
                return pos + 1
            else:
                pos += 1
        raise ValueError("unterminated JavaScript string")

    def template(start: int) -> int:
        mask(start, start + 1)
        pos = start + 1
        while pos < size:
            if source[pos] == "\\":
                mask(pos, min(pos + 2, size))
                pos += 2
            elif source[pos] == "`":
                mask(pos, pos + 1)
                return pos + 1
            elif source.startswith("${", pos):
                mask(pos, pos + 2)
                pos = code(pos + 2, interpolation=True)
            else:
                mask(pos, pos + 1)
                pos += 1
        raise ValueError("unterminated JavaScript template")

    def regex_literal(start: int) -> int:
        pos = start + 1
        in_class = False
        while pos < size:
            if source[pos] == "\\":
                pos += 2
                continue
            if source[pos] == "[":
                in_class = True
            elif source[pos] == "]":
                in_class = False
            elif source[pos] == "/" and not in_class:
                mask(start, pos + 1)
                return pos + 1
            elif source[pos] == "\n":
                break
            pos += 1
        raise ValueError("unterminated JavaScript regex")

    def starts_regex(pos: int) -> bool:
        previous = pos - 1
        while previous >= 0 and chars[previous].isspace():
            previous -= 1
        if previous < 0 or chars[previous] in "(=:[,!&|?{;":
            return True
        end = previous + 1
        while previous >= 0 and (chars[previous].isalnum() or chars[previous] == "_"):
            previous -= 1
        before_word = previous
        while before_word >= 0 and chars[before_word].isspace():
            before_word -= 1
        if before_word >= 0 and chars[before_word] == ".":
            return False
        return "".join(chars[previous + 1:end]) in {"return", "throw", "case", "yield", "await"}

    def code(pos: int, interpolation: bool = False) -> int:
        depth = 0
        while pos < size:
            if source.startswith("//", pos):
                end = source.find("\n", pos)
                end = size if end < 0 else end
                mask(pos, end)
                pos = end
            elif source.startswith("/*", pos):
                end = source.find("*/", pos + 2)
                if end < 0:
                    raise ValueError("unterminated JavaScript comment")
                mask(pos, end + 2)
                pos = end + 2
            elif source[pos] == "/" and starts_regex(pos):
                pos = regex_literal(pos)
                chars[pos - 1] = "0"  # Literal is an expression end, not whitespace.
            elif source[pos] in ("'", '"'):
                pos = quoted(pos)
                chars[pos - 1] = "0"
            elif source[pos] == "`":
                pos = template(pos)
                chars[pos - 1] = "0"
            elif source[pos] == "{":
                depth += 1
                pos += 1
            elif source[pos] == "}":
                if interpolation and depth == 0:
                    mask(pos, pos + 1)
                    return pos + 1
                depth -= 1
                pos += 1
            else:
                pos += 1
        if interpolation:
            raise ValueError("unterminated JavaScript interpolation")
        return pos

    code(0)
    return "".join(chars)


def disabled_lines(path: str, source: str) -> set[int]:
    """Return executable test-disable locations, excluding quoted evidence."""
    suffix = Path(path).suffix.lower()
    if suffix == ".py":
        code = _python_code(source)
        pattern = r"(?:\b[A-Za-z_]\w*\s*)?\.\s*(?:skip|skipif|only)\b"
    elif suffix == ".rs":
        code = _rust_code(source)
        pattern = r"#[ \t]*\[[ \t]*ignore\b"
    elif suffix in (".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"):
        code = _javascript_code(source)
        pattern = r"(?:\b[A-Za-z_$][\w$]*\s*)?\.\s*(?:skip|only)\s*\(|\b(?:xit|xdescribe|fit|fdescribe)\s*\("
    else:
        return set()
    found = set()
    for match in re.finditer(pattern, code):
        first = code.count("\n", 0, match.start()) + 1
        last = code.count("\n", 0, match.end()) + 1
        found.update(range(first, last + 1))
    return found


def _git(*args: str) -> str:
    return subprocess.check_output(
        ["git", "-c", "core.quotepath=false", *args], encoding="utf-8", errors="strict"
    )


def added_lines(diff: str) -> dict[str, set[int]]:
    changed: dict[str, set[int]] = {}
    path = ""
    line = 0
    for text in diff.splitlines():
        if text.startswith("+++ b/"):
            path = text[6:]
            changed.setdefault(path, set())
        elif text.startswith("@@"):
            line = int(re.search(r"\+(\d+)", text).group(1))
        elif text.startswith("+") and not text.startswith("+++"):
            if path:
                changed[path].add(line)
            line += 1
        elif text.startswith(" "):
            line += 1
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base")
    args = parser.parse_args()
    revision = "HEAD" if args.base else ""
    diff_args = [f"{args.base}...HEAD"] if args.base else ["--cached"]
    supported = (".py", ".rs", ".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs")
    diff = _git("diff", "--no-renames", "-U0", "--no-color", "--diff-filter=ACMR", *diff_args,
                "--", *(f":(icase)*{suffix}" for suffix in supported))
    failures = []
    for path, additions in added_lines(diff).items():
        if Path(path).suffix.lower() not in supported:
            continue
        source = _git("show", f"{revision}:{path}").lstrip("\ufeff")
        for line in sorted(disabled_lines(path, source) & additions):
            failures.append(f"{path}:{line}: executable test disable added")
    for failure in failures:
        print(failure)
    return int(bool(failures))


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, subprocess.CalledProcessError, tokenize.TokenError, SyntaxError, ValueError, UnicodeError) as error:
        print(f"Test-disable guard could not inspect source: {error}", file=sys.stderr)
        raise SystemExit(2)
