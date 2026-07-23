"""LPOS-12 regression tests: the stdlib structural schema gate.

A syntactically valid JSON file that is meta-invalid as a JSON Schema must
FAIL the gate, with or without the optional jsonschema dependency.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from lpos_engine import schema_check
from lpos_engine.schema_check import (
    SchemaCheckError,
    check_schema,
    check_schema_files,
    validate_for_cli,
)

RUNTIME_ROOT = Path(__file__).resolve().parents[1]
PACKAGED_SCHEMA_ROOT = RUNTIME_ROOT / "src" / "lpos_engine" / "schemas"
RELEASE_SCHEMA_ROOT = RUNTIME_ROOT / "schemas"


class ShippedSchemasPassTests(unittest.TestCase):
    def test_all_17_packaged_schemas_pass_structural_validation(self):
        paths = sorted(PACKAGED_SCHEMA_ROOT.glob("*.schema.json"))
        self.assertEqual(len(paths), 20)
        results = check_schema_files(paths)
        for name, problems in results.items():
            with self.subTest(schema=name):
                self.assertEqual(problems, [])

    def test_all_17_release_schemas_pass_structural_validation(self):
        paths = sorted(RELEASE_SCHEMA_ROOT.glob("*.schema.json"))
        self.assertEqual(len(paths), 20)
        results = check_schema_files(paths)
        for name, problems in results.items():
            with self.subTest(schema=name):
                self.assertEqual(problems, [])

    def test_validate_for_cli_matches_cli_result_contract(self):
        result = validate_for_cli()
        self.assertEqual(sorted(result), ["root", "schemas", "status"])
        self.assertEqual(result["schemas"], 20)
        self.assertIsInstance(result["root"], str)
        self.assertIn(
            result["status"],
            ("valid (structural)", "valid (structural+jsonschema)"),
        )

    def test_validate_for_cli_reports_extended_status_when_jsonschema_available(self):
        try:
            import jsonschema  # noqa: F401
        except ImportError:
            expected = "valid (structural)"
        else:
            expected = "valid (structural+jsonschema)"
        self.assertEqual(validate_for_cli(RELEASE_SCHEMA_ROOT)["status"], expected)

    def test_validate_for_cli_rejects_empty_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(SchemaCheckError):
                validate_for_cli(directory)


class MetaInvalidSchemaTests(unittest.TestCase):
    def assert_problem(self, document, fragment):
        problems = check_schema(document)
        self.assertTrue(problems, f"expected problems for {document!r}")
        joined = "\n".join(problems)
        self.assertIn(fragment, joined, joined)
        return problems

    def test_misspelled_type_name_fails_with_useful_message(self):
        problems = self.assert_problem({"type": "strnig"}, "strnig")
        self.assertIn("not a valid JSON Schema type name", problems[0])
        self.assertIn("string", problems[0])  # message lists the valid names

    def test_invalid_type_in_type_array_fails(self):
        self.assert_problem({"type": ["string", "nul"]}, "'nul'")

    def test_required_as_string_fails(self):
        self.assert_problem({"required": "name"}, "must be a list of property names")

    def test_required_with_non_string_entry_fails(self):
        self.assert_problem({"required": ["ok", 5]}, "property names must be strings")

    def test_properties_as_array_fails(self):
        self.assert_problem(
            {"properties": [{"name": {"type": "string"}}]},
            "must be an object mapping names to schemas",
        )

    def test_dangling_ref_fails(self):
        self.assert_problem(
            {"$defs": {"real": {"type": "string"}}, "$ref": "#/$defs/missing"},
            "dangling reference",
        )

    def test_resolvable_refs_pass(self):
        document = {
            "$defs": {"item": {"type": "string"}},
            "properties": {"name": {"$ref": "#/$defs/item"}},
            "allOf": [{"$ref": "#/properties/name"}, {"$ref": "#"}],
        }
        self.assertEqual(check_schema(document), [])

    def test_external_ref_is_rejected_offline(self):
        self.assert_problem(
            {"$ref": "https://example.com/other.schema.json"},
            "cannot be verified by the offline structural validator",
        )

    def test_bad_pattern_fails(self):
        self.assert_problem({"pattern": "("}, "invalid regular expression")

    def test_empty_enum_fails(self):
        self.assert_problem({"enum": []}, "non-empty list")

    def test_numeric_keywords_require_numbers(self):
        self.assert_problem({"minimum": "3"}, "must be a number")
        self.assert_problem({"maxLength": -1}, "non-negative integer")
        self.assert_problem({"minItems": "2"}, "non-negative integer")
        self.assert_problem({"minLength": True}, "non-negative integer")

    def test_nested_subschema_problems_are_located(self):
        document = {
            "properties": {
                "steps": {"items": {"type": "strnig"}},
            }
        }
        problems = self.assert_problem(document, "strnig")
        self.assertIn("#/properties/steps/items/type", problems[0])

    def test_allof_must_be_non_empty_list_of_schemas(self):
        self.assert_problem({"allOf": {}}, "must be a list of schemas")
        self.assert_problem({"allOf": []}, "non-empty list of schemas")
        self.assert_problem({"anyOf": ["nope"]}, "schema must be an object or a boolean")

    def test_items_array_form_is_rejected_for_draft_2020_12(self):
        self.assert_problem({"items": [{"type": "string"}]}, "single schema")

    def test_schema_document_must_be_object_or_boolean(self):
        self.assert_problem(["not", "a", "schema"], "object or a boolean")


class SchemaFileGateTests(unittest.TestCase):
    def write(self, directory, name, text):
        path = Path(directory) / name
        path.write_text(text, encoding="utf-8")
        return path

    def test_duplicate_keys_are_detected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(
                directory,
                "dup.schema.json",
                '{"type": "object", "type": "object"}',
            )
            results = check_schema_files([path])
            self.assertTrue(
                any("duplicate object key" in p for p in results["dup.schema.json"]),
                results,
            )

    def test_invalid_json_is_reported(self):
        with tempfile.TemporaryDirectory() as directory:
            path = self.write(directory, "broken.schema.json", "{not json")
            results = check_schema_files([path])
            self.assertTrue(
                any("invalid JSON" in p for p in results["broken.schema.json"])
            )

    def test_meta_invalid_file_fails_the_install_gate(self):
        """The audit scenario: valid JSON, invalid schema -> gate raises."""
        with tempfile.TemporaryDirectory() as directory:
            self.write(
                directory,
                "bad.schema.json",
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "strnig",
                        "required": "name",
                        "properties": [{"name": {"type": "string"}}],
                        "$ref": "#/$defs/missing",
                    }
                ),
            )
            with self.assertRaises(SchemaCheckError) as caught:
                validate_for_cli(directory)
            message = str(caught.exception)
            self.assertIn("bad.schema.json", message)
            self.assertIn("strnig", message)
            self.assertIn("required", message)
            self.assertIn("dangling reference", message)

    def test_gate_passes_a_directory_of_valid_schemas(self):
        with tempfile.TemporaryDirectory() as directory:
            self.write(
                directory,
                "good.schema.json",
                json.dumps(
                    {
                        "$schema": "https://json-schema.org/draft/2020-12/schema",
                        "type": "object",
                        "properties": {"name": {"type": "string", "minLength": 1}},
                        "required": ["name"],
                        "additionalProperties": False,
                    }
                ),
            )
            result = validate_for_cli(directory)
            self.assertEqual(result["schemas"], 1)
            self.assertTrue(result["status"].startswith("valid (structural"))


class ModuleContractTests(unittest.TestCase):
    def test_module_is_stdlib_only(self):
        """The gate must work on a clean offline install with no extras."""
        import importlib.util

        spec = importlib.util.find_spec("lpos_engine.schema_check")
        source = Path(spec.origin).read_text(encoding="utf-8")
        # jsonschema may only ever appear inside a guarded optional import.
        for line in source.splitlines():
            stripped = line.strip()
            if stripped.startswith(("import ", "from ")) and "jsonschema" in stripped:
                self.assertIn("from jsonschema", stripped)
        self.assertNotIn("import requests", source)

    def test_check_schema_returns_list_of_strings(self):
        problems = schema_check.check_schema({"type": 12})
        self.assertIsInstance(problems, list)
        self.assertTrue(all(isinstance(item, str) for item in problems))


if __name__ == "__main__":
    unittest.main()
