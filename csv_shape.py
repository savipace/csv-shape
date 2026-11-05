"""Check the structure of UTF-8 CSV and TSV files."""

import argparse
from collections import Counter
import csv
import io
import json
from pathlib import Path
import sys


DELIMITERS = {"comma": ",", "tab": "\t", "semicolon": ";"}


def delimiter_for(path, override):
    inferred = "tab" if path.suffix.lower() == ".tsv" else "comma"
    return DELIMITERS[override or inferred]


def header_issues(header, counts):
    if not header:
        yield "expected a header row"
    for name, count in counts.items():
        if not name.strip():
            yield "column names must not be blank"
        elif count > 1:
            yield f"duplicate column name {name!r}"


def header_changes(expected, actual, actual_counts):
    expected_names = set(expected)
    for name in expected:
        if name not in actual_counts:
            yield f"baseline column {name!r} is missing"
    for name in actual:
        if name not in expected_names:
            yield f"column {name!r} is new relative to the baseline"
    shared_expected = [name for name in expected if name in actual_counts]
    shared_actual = [name for name in actual if name in expected_names]
    if shared_expected != shared_actual:
        yield "columns shared with the baseline header were reordered"


def validate(stream, delimiter, required, unique, expected_header=None):
    """Yield (line number, message) pairs in file order."""
    reader = csv.reader(stream, delimiter=delimiter, strict=True)
    try:
        header = next(reader, [])
        if not header:
            yield 1, "expected a header row"
            return

        headers = Counter(header)
        invalid_header = False
        for message in header_issues(header, headers):
            yield 1, message
            invalid_header = True
        if expected_header is not None and not invalid_header:
            for message in header_changes(expected_header, header, headers):
                yield 1, message
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
    parser.add_argument(
        "--baseline", type=Path, metavar="FILE",
        help="require the same column names and order as a reference file",
    )
    args = parser.parse_args(argv)
    path = Path(args.file)
    delimiter = delimiter_for(path, args.delimiter)
    required = dict.fromkeys(args.required)
    unique = dict.fromkeys(args.unique)
    label = "<stdin>" if args.file == "-" else args.file

    def report(message, line=None, file=label):
        if args.format == "jsonl":
            diagnostic = {"file": file, "line": line, "message": message}
            print(json.dumps(diagnostic), file=sys.stderr)
        else:
            location = f"{file}:{line}" if line is not None else file
            print(f"{location}: {message}", file=sys.stderr)

    expected_header = None
    if args.baseline is not None:
        baseline_label = str(args.baseline)
        baseline_delimiter = delimiter_for(args.baseline, args.delimiter)
        try:
            with args.baseline.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.reader(stream, delimiter=baseline_delimiter, strict=True)
                expected_header = next(reader, [])
        except (OSError, UnicodeError, csv.Error) as error:
            report(f"could not read baseline header: {error}", file=baseline_label)
            return 2
        errors = list(header_issues(expected_header, Counter(expected_header)))
        if errors:
            for error in errors:
                report(f"invalid baseline header: {error}", 1, file=baseline_label)
            return 2

    status = 0
    try:
        if args.file == "-":
            stream = io.TextIOWrapper(sys.stdin.buffer, encoding="utf-8-sig", newline="")
        else:
            stream = path.open(encoding="utf-8-sig", newline="")
        try:
            for line, message in validate(stream, delimiter, required, unique, expected_header):
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
