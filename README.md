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

## Catch changes to a published dataset

Keep a header-only file in version control to describe the columns your users
already depend on. Check every new export against it before publishing.

```sh
printf 'sku,name,stock\n' > inventory-contract.csv
python3 csv_shape.py example.csv --baseline inventory-contract.csv --required sku --unique sku
```

If an export changes `stock` to `quantity`, the check reports both the missing
`stock` column and the new `quantity` column. It also catches columns moved to
a different position. This helps when downstream scripts read fields by name
or by position. The data rows can change freely within the other rules you set.

The baseline can also be a previous export. Only its first CSV or TSV record is
used as the contract. Without `--delimiter`, the separator is inferred for each
file separately. An explicit `--delimiter` applies to both files.

## Use in a pipeline

Pass `-` to validate standard input. Diagnostics go to standard error, so the
command also works in shell scripts and CI.

```sh
python3 csv_shape.py - --required sku --unique sku --format jsonl < example-invalid.csv
```

Each JSON Lines diagnostic has `file`, `line`, and `message` fields. For read
errors, `line` is null. For TSV on standard input, pass `--delimiter tab`.

## Live example with USGS data

The [USGS earthquake feed workflow](https://github.com/savipace/csv-shape/actions/workflows/usgs-feed.yml)
downloads the rolling seven-day M2.5+ CSV from the [USGS Earthquake Hazards Program](https://earthquake.usgs.gov/earthquakes/feed/v1.0/csv.php).
Before it publishes counts by UTC date in the run summary, `csv-shape` checks
row widths, required IDs and timestamps, and duplicate IDs. A failed check
stops the report. It runs on Mondays and can also be run on demand.

## Validation rules

- The first row must contain nonblank, distinct column names. Each data row must have the same number of fields as the header.
- Repeat `--required COLUMN` to require named columns and reject empty or whitespace-only values in them.
- Repeat `--unique COLUMN` to require named columns and flag duplicate nonblank values. Names and values are compared exactly. Pair this with `--required` when blank values should also fail.
- Input uses UTF-8, with or without a BOM. Quoted fields can contain separators and newlines.
- Files ending in `.tsv` use tabs by default. Other files default to commas. Override the separator with `--delimiter comma`, `--delimiter tab`, or `--delimiter semicolon`.

Valid files exit with status `0`. Candidate validation or parse errors exit with status `1`. An invalid baseline, unreadable file, invalid UTF-8, or incorrect command-line usage exits with status `2`.

Rows are read one at a time. Each `--unique` column stores its distinct values in memory.

## Contributing

Run the tests with `python3 -m unittest -v`. For a bug report, include the command and a small example with synthetic data that reproduces the problem.

Released under the [MIT License](LICENSE).
