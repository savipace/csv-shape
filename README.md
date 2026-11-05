# csv-shape

Check that a CSV or TSV export has the columns and row structure your import expects. The command prints errors with file names and line numbers, so you can find the rows to fix before an import or fail a CI step when an export changes.

## Quick start

Requires Python 3.10 or newer. Run the script from the repository root.

```sh
python3 csv_shape.py example.csv --required sku --unique sku
```

To see the diagnostics for a duplicate SKU and a row with too few fields, run:

```sh
python3 csv_shape.py example-invalid.csv --required sku --unique sku
```

```text
example-invalid.csv:3: duplicate value in 'sku' (first seen on line 2)
example-invalid.csv:4: expected 3 fields, found 2
```

## Use in a pipeline

Pass `-` to validate standard input. Diagnostics go to standard error, so the
command also works in shell scripts and CI.

```sh
python3 csv_shape.py - --required sku --unique sku --format jsonl < example-invalid.csv
```

Each JSON Lines diagnostic has `file`, `line`, and `message` fields. For read
errors, `line` is null. For TSV on standard input, pass `--delimiter tab`.

## Validation rules

- The first row must contain nonblank, distinct column names. Each data row must have the same number of fields as the header.
- Repeat `--required COLUMN` to require named columns and reject empty or whitespace-only values in them.
- Repeat `--unique COLUMN` to require named columns and flag duplicate nonblank values. Names and values are compared exactly. Pair this with `--required` when blank values should also fail.
- Input uses UTF-8, with or without a BOM. Quoted fields can contain separators and newlines.
- Files ending in `.tsv` use tabs by default. Other files default to commas. Override the separator with `--delimiter comma`, `--delimiter tab`, or `--delimiter semicolon`.

Valid files exit with status `0`. Validation or parse errors exit with status `1`. An unreadable file, invalid UTF-8, or incorrect command-line usage exits with status `2`.

Rows are read one at a time. Each `--unique` column stores its distinct values in memory.

## Contributing

Run the tests with `python3 -m unittest -v`. For a bug report, include the command and a small example with synthetic data that reproduces the problem.

Released under the [MIT License](LICENSE).
