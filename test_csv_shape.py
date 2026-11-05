import contextlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from csv_shape import main, validate


class ValidationTests(unittest.TestCase):
    def errors(self, content, required=(), unique=(), delimiter=","):
        return list(validate(io.StringIO(content, newline=""), delimiter, required, unique))

    def test_quoted_fields_with_newlines(self):
        self.assertEqual(self.errors('id,notes\n1,"First line\nsecond, line"\n'), [])

    def test_errors_report_start_of_multiline_record(self):
        self.assertEqual(
            self.errors('id,notes\n1,a\n1,"first\nsecond"\n2\n', unique=("id",)),
            [
                (3, "duplicate value in 'id' (first seen on line 2)"),
                (5, "expected 2 fields, found 1"),
            ],
        )

    def test_required_values_and_optional_unique_blanks(self):
        self.assertEqual(
            self.errors("id,alias\n,\n2,\n", required=("id",), unique=("alias",)),
            [(2, "required column 'id' is blank")],
        )

    def test_invalid_headers(self):
        self.assertEqual(self.errors(""), [(1, "expected a header row")])
        self.assertEqual(
            self.errors("id,id, \n", required=("name",)),
            [
                (1, "duplicate column name 'id'"),
                (1, "column names must not be blank"),
                (1, "missing column 'name'"),
            ],
        )

    def test_unterminated_quote(self):
        self.assertEqual(
            self.errors('id,notes\n1,"unterminated\n'),
            [(2, "could not parse delimited text: unexpected end of data")],
        )


class CommandTests(unittest.TestCase):
    def test_tab_inference_with_utf8_bom(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "inventory.tsv"
            path.write_text("id\tname\r\n1\tPen\r\n", encoding="utf-8-sig")
            self.assertEqual(main([str(path), "--required", "name"]), 0)

    def test_stdin_with_json_lines(self):
        script = Path(__file__).with_name("csv_shape.py")
        result = subprocess.run(
            [sys.executable, str(script), "-", "--required", "id", "--format", "jsonl"],
            input=b"id,name\n,Pen\n",
            capture_output=True,
        )
        self.assertEqual(result.returncode, 1)
        self.assertEqual(result.stdout, b"")
        self.assertEqual(
            json.loads(result.stderr),
            {"file": "<stdin>", "line": 2, "message": "required column 'id' is blank"},
        )

    def test_validation_and_read_failures_have_distinct_exit_codes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "inventory.csv"
            path.write_text("id,name\n1\n", encoding="utf-8")
            stderr = io.StringIO()
            with contextlib.redirect_stderr(stderr):
                self.assertEqual(main([str(path)]), 1)
                self.assertEqual(main([str(path.with_suffix(".tsv"))]), 2)
            self.assertIn("inventory.csv:2: expected 2 fields, found 1", stderr.getvalue())
            self.assertIn("inventory.tsv: could not read UTF-8 input", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
