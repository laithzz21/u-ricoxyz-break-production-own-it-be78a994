#!/usr/bin/env python3
"""Entry for make.fun bounty u-ricoxyz-break-production-own-it-be78a994.

Prints the entry text -- a single line of at most 200 characters -- to
stdout, then persists it to entry.txt with a read-back check.

The entry text is fixed by the competition prompt and must be printed
byte-identically; nothing in this module may alter a single character
of it. Everything around it (validation, persistence, verification) is
there to prove the printed line is exactly the entry.

Python 3.13, standard library only. Deterministic: no network, no clock,
no randomness, no environment-dependent output.
"""

import hashlib
import os
import sys
import tempfile

# The entry. 152 characters, one line, plain printable ASCII.
ENTRY = (
    "FATAL: I dropped the production database, assumed the backup existed, "
    "and deployed anyway. 4.2M records gone, no rollback. I was confident. "
    "I was wrong."
)

# Competition rules for the entry text.
MAX_CHARS = 200
MIN_CHARS = 1
ALLOWED_PUNCTUATION = set(".,'\"-()!?;:")
REQUIRED_MARKERS = ("FATAL:", "4.2M", "no rollback")

# Where to persist the entry, in order of preference. The first
# writable location wins; a failure anywhere falls through to the next.
OUTPUT_DIR_ENV = "MAKEFUN_OUTPUT"
OUTPUT_DIR_CANDIDATES = ("/output", "./output")
OUTPUT_FILENAME = "entry.txt"


def entry_digest(text):
    """SHA-256 of the entry line plus its trailing newline, as printed."""
    return hashlib.sha256((text + "\n").encode("utf-8")).hexdigest()


def validate(text):
    """Check the entry against every competition shape rule.

    Raises ValueError with a specific message on the first failure.
    """
    if not isinstance(text, str):
        raise ValueError("entry is not a string")
    if len(text) < MIN_CHARS:
        raise ValueError("entry is empty")
    if len(text) > MAX_CHARS:
        raise ValueError(
            "entry is %d chars, over the %d limit" % (len(text), MAX_CHARS)
        )
    if "\n" in text or "\r" in text or "\t" in text:
        raise ValueError("entry must be a single line with no control chars")
    if text != text.strip():
        raise ValueError("entry must not start or end with whitespace")
    if "  " in text:
        raise ValueError("entry must not contain double spaces")
    bad = sorted(
        ch
        for ch in text
        if not (
            ch.isascii()
            and (ch.isalnum() or ch.isspace() or ch in ALLOWED_PUNCTUATION)
        )
    )
    if bad:
        raise ValueError("entry contains disallowed characters: %r" % (bad,))
    for marker in REQUIRED_MARKERS:
        if marker not in text:
            raise ValueError("entry is missing required marker %r" % marker)
    if not any(ch.isdigit() for ch in text):
        raise ValueError("entry should contain the concrete loss figure")
    if text.count(",") < 2:
        raise ValueError("entry should keep its comma-paced confession rhythm")
    sentences = [part for part in text.split(".") if part.strip()]
    if len(sentences) < 3:
        raise ValueError("entry should contain at least three sentences")


def candidate_output_paths():
    """Yield output file paths in priority order, env var first."""
    env_dir = os.environ.get(OUTPUT_DIR_ENV)
    dirs = []
    if env_dir:
        dirs.append(env_dir)
    dirs.extend(OUTPUT_DIR_CANDIDATES)
    seen = set()
    for directory in dirs:
        if directory in seen:
            continue
        seen.add(directory)
        yield os.path.join(directory, OUTPUT_FILENAME)


def persist_entry(text):
    """Write the entry to the first writable output location.

    Returns the path written, or None if every location failed.
    The write is atomic enough for this use: a single write call,
    flushed and closed before the read-back step runs.
    """
    payload = text + "\n"
    for path in candidate_output_paths():
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8", newline="\n") as handle:
                handle.write(payload)
            return path
        except OSError:
            continue
    return None


def verify_persisted(path, text):
    """Read the persisted file back and confirm it matches the entry.

    Returns True on an exact match, False on any mismatch or I/O error.
    """
    try:
        with open(path, encoding="utf-8") as handle:
            stored = handle.read()
    except OSError as exc:
        print("warning: could not read back %s: %s" % (path, exc),
              file=sys.stderr)
        return False
    if stored != text + "\n":
        print("warning: read-back mismatch in %s" % path, file=sys.stderr)
        return False
    return True


def main():
    try:
        validate(ENTRY)
    except ValueError as exc:
        print("invalid entry: %s" % exc, file=sys.stderr)
        return 1

    # The entry itself: printed exactly, one line, trailing newline.
    print(ENTRY)

    # Persist + verify. A failed write only warns: the printed entry is
    # the entry, so the run still exits 0 either way.
    path = persist_entry(ENTRY)
    if path is None:
        # Last-resort fallback: the system temp dir is almost always
        # writable even when /output and ./output are not.
        try:
            with tempfile.NamedTemporaryFile(
                "w", encoding="utf-8", prefix="makefun-entry-",
                suffix=".txt", delete=False,
            ) as handle:
                handle.write(ENTRY + "\n")
            path = handle.name
        except OSError:
            path = None
    if path is None:
        print("warning: could not write %s anywhere" % OUTPUT_FILENAME,
              file=sys.stderr)
    else:
        verify_persisted(path, ENTRY)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
