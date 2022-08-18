from unittest import TestCase

from pyspc_write_jdx.data_records import DataRecord, ValidationError


class GenericDataRecordTestCase(TestCase):
    def test_init(self):
        ldr = DataRecord(
            label="TITLE", format="STRING", required=True, description="Some comment"
        )
        self.assertEqual(ldr.label, "TITLE")
        self.assertEqual(ldr.format, "STRING")
        self.assertEqual(ldr.required, True)
        self.assertEqual(ldr.description, "Some comment")
        self.assertIsNone(ldr.choices)
        self.assertIsNone(ldr.comment)
        self.assertIsNone(ldr.value)

    def test_str(self):
        ldr = DataRecord(label="TITLE", format="STRING")
        self.assertEqual(str(ldr), "##TITLE=")

        ldr.value = "SOMETHING"
        self.assertEqual(str(ldr), "##TITLE= SOMETHING")

        ldr.comment = "comment"
        self.assertEqual(str(ldr), "##TITLE= SOMETHING  $$ comment")

        # Test wrapping long lines
        ldr.value = " ".join(["short"] * 20)
        self.assertEqual(
            str(ldr),
            "##TITLE= short short short short short short short short short short short short  $$ comment\nshort short short short short short short short",
        )

    def test_default_validation(self):
        ldr = DataRecord(
            label="TITLE", format="STRING", required=True, choices=["A", "B"]
        )
        validation = ldr.validate(None)

        self.assertEqual(len(validation), 1)
        self.assertEqual(validation[0], "DATA-LABEL '##TITLE=' is required.")

        ldr.value = "C"
        validation = ldr.validate(None)
        self.assertEqual(len(validation), 1)
        self.assertEqual(
            validation[0],
            "Unexpected value for DATA-LABEL '##TITLE='. Available values ['A', 'B'].",
        )

    def test_custom_validation(self):
        def _dummy_validator(dr, *args, **kwargs):
            if len(dr.value) < 10:
                raise ValidationError("Value is too short")
            return True

        ldr = DataRecord(
            label="TITLE",
            format="STRING",
            choices=["A", "B"],
            validators=[_dummy_validator],
        )
        ldr.value = "C"
        validation = ldr.validate(None)

        self.assertEqual(len(validation), 2)
        self.assertEqual(
            validation[0],
            "Unexpected value for DATA-LABEL '##TITLE='. Available values ['A', 'B'].",
        )
        self.assertEqual(validation[1], "Value is too short")
