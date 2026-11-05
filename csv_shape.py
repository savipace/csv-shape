"""Check the structure of UTF-8 CSV and TSV files."""

import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path
import sys


DELIMITERS = {"comma": ",", "tab": "\t", "semicolon": ";"}


def validate(stream, delimiter, required, unique):
    """Yield (line number, message) pairs in file order."""
    reader = csv.reader(stream, delimiter=delimiter, strict=True)
    try:
        header = next(reader, None)
        if not header:
            yield 1, "expected a header row"
            return

        headers = Counter(header)
        invalid_header = False
        for name, count in headers.items():
            if not name.strip():
                yield 1, "column names must not be blank"
                invalid_header = True
            elif count > 1:
                yield 1, f"duplicate column name {name!r}"
                invalid_header = True
        for name in dict.fromkeys([*required, *unique]):
            if name not in headers:
                yield 1, f"missing column {name!r}"
                invalid_header = True
        if invalid_header:
            return

        required_columns = [(header.index(name), name) for name in required]
        unique_columns = [(header.index(name), name, {}) for name in unique]
        width = len(header)

        while True:
            line = reader.line_num + 1
            row = next(reader, None)
            if row is None:
                return
            if len(row) != width:
                yield line, f"expected {width} fields, found {len(row)}"
                continue
            for index, name in required_columns:
                if not row[index].strip():
                    yield line, f"required column {name!r} is blank"
            for index, name, seen in unique_columns:
                value = row[index]
                if not value.strip():
                    continue
                first_line = seen.setdefault(value, line)
                if first_line != line:
                    yield line, f"duplicate value in {name!r} (first seen on line {first_line})"
    except csv.Error as error:
        yield max(1, reader.line_num), f"could not parse delimited text: {error}"


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", help="path to a CSV or TSV file, or - for standard input")
    parser.add_argument(
        "--delimiter", choices=DELIMITERS,
        help="field separator (defaults to tab for .tsv and comma otherwise)",
    )
    parser.add_argument(
        "--required", metavar="COLUMN", action="append", default=[],
        help="require a named column to contain a value in each row (repeatable)",
    )
    parser.add_argument(
        "--unique", metavar="COLUMN", action="append", default=[],
        help="require distinct nonblank values in a named column (repeatable)",
    )
    parser.add_argument(
        "--format", choices=("text", "jsonl"), default="text",
        help="write diagnostics as plain text or JSON Lines",
    )
    args = parser.parse_args(argv)
    path = Path(args.file)
    inferred = "tab" if path.suffix.lower() == ".tsv" else "comma"
    delimiter = DELIMITERS[args.delimiter or inferred]
    required = dict.fromkeys(args.required)
    unique = dict.fromkeys(args.unique)
    label = "<stdin>" if args.file == "-" else args.file

    def report(message, line=None):
        if args.format == "jsonl":
            diagnostic = {"file": label, "line": line, "message": message}
            print(json.dumps(diagnostic), file=sys.stderr)
        else:
            location = f"{label}:{line}" if line is not None else label
            print(f"{location}: {message}", file=sys.stderr)

    status = 0
    try:
        if args.file == "-":
            stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig", newline="")
        else:
            stream = path.open(encoding="utf-8-sig", newline="")
        try:
            for line, message in validate(stream, delimiter, required, unique):
                report(message, line)
                status = 1
        finally:
            if args.file == "-":
                stream.detach()
            else:
                stream.close()
    except (OSError, UnicodeError) as error:
        report(f"could not read UTF-8 input: {error}")
        return 2
    return status


if __name__ == "__main__":
    raise SystemExit(main())
