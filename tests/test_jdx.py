from unittest import TestCase

from pyspc_write_jdx.data_records import StringDataRecord
from pyspc_write_jdx.jdx import CompoundJDX, SimpleJDX


class SimpleJDXTestCase(TestCase):
    def test_init(self):
        jdx = SimpleJDX(
            title="Some title",
            data_type="IR",
            xypoints=[[1, 2, 3], [4, 5, 6]],
        )
        self.assertEqual(jdx.title.value, "Some title")
        self.assertEqual(jdx.jcamp_dx.value, "5.01")
        self.assertEqual(jdx.data_type.value, "IR")
        self.assertEqual(jdx._data_table_record_name, "xypoints")
        self.assertEqual(jdx._data_table_record.data, [[1, 2, 3], [4, 5, 6]])
        self.assertEqual(jdx.firstx.value, 1)
        self.assertEqual(jdx.lastx.value, 3)
        self.assertEqual(jdx.npoints.value, 3)
        self.assertEqual(jdx.xfactor.value, 1)
        self.assertEqual(jdx.yfactor.value, 1)

    def test_custom_output_data_records(self):
        # Create custom class
        class CustomSimpleJDX(SimpleJDX):
            my_custom_record = StringDataRecord(
                "$MY CUSTOM RECORD", choices=["A", "B"], required=True
            )

        # Validate the order of the data records
        jdx = CustomSimpleJDX(
            title="title", my_custom_record="A", xypoints=[[1, 2], [3, 4]]
        )
        self.assertEqual(jdx._all_data_records()[0], "title")
        self.assertEqual(jdx._all_data_records()[-1], "my_custom_record")

    def test_output_string(self):
        jdx = SimpleJDX(
            title="Some title",
            data_type="IR",
            xunits="l/CM",
            origin="My origin",
            owner="Me",
            xypoints=[[1, 2, 3], [4, 5, 6]],
        )
        self.assertEqual(
            repr(jdx),
            """##TITLE= Some title
##JCAMP-DX= 5.01
##DATA TYPE= IR
##XUNITS= l/CM
##YUNITS=
##FIRSTX= 1
##LASTX= 3
##XFACTOR= 1
##YFACTOR= 1
##NPOINTS= 3
##ORIGIN= My origin
##OWNER= Me
##XYPOINTS= (XY..XY)
1.0000, 4.0000
2.0000, 5.0000
3.0000, 6.0000
##END=""",
        )

        jdx.xypoints.single_column = False
        self.assertEqual(
            repr(jdx),
            """##TITLE= Some title
##JCAMP-DX= 5.01
##DATA TYPE= IR
##XUNITS= l/CM
##YUNITS=
##FIRSTX= 1
##LASTX= 3
##XFACTOR= 1
##YFACTOR= 1
##NPOINTS= 3
##ORIGIN= My origin
##OWNER= Me
##XYPOINTS= (XY..XY)
1.0000, 4.0000 : 2.0000, 5.0000 : 3.0000, 6.0000
##END=""",
        )

        with self.assertWarnsRegex(
            UserWarning, ".*DATA-LABEL '##YUNITS=' is required.*"
        ):
            s = jdx.to_string()  # noqa: F841

        with self.assertWarnsRegex(
            UserWarning, ".*Unexpected value for DATA-LABEL '##DATA TYPE='.*"
        ):
            s = jdx.to_string()  # noqa: F841


class CompoundJDXTestCase(TestCase):
    def test_init(self):
        jdx_link = CompoundJDX("test")
        self.assertEqual(jdx_link.title.value, "test")
        self.assertEqual(jdx_link.jcamp_dx.value, "5.01")
        self.assertEqual(jdx_link.data_type.value, "LINK")
        self.assertEqual(jdx_link.block_count.value, 0)
        self.assertEqual(jdx_link.blocks, [])

        jdx_block = SimpleJDX(
            title="Some title", data_type="IR", xypoints=[[1, 2, 3], [4, 5, 6]]
        )
        jdx_link = CompoundJDX("test", jdx_block)
        self.assertEqual(jdx_link.block_count.value, 1)
        self.assertEqual(len(jdx_link.blocks), 1)
        self.assertEqual(jdx_link.blocks[0].title.value, "Some title")

        jdx_block2 = SimpleJDX(
            title="Some title2", data_type="IR", xydata=[[1, 2, 3], [4, 5, 6]]
        )
        jdx_link = CompoundJDX("test", jdx_block, jdx_block2)
        self.assertEqual(jdx_link.block_count.value, 2)
        self.assertEqual(len(jdx_link.blocks), 2)
        self.assertEqual(jdx_link.blocks[0].title.value, "Some title")
        self.assertEqual(jdx_link.blocks[1].title.value, "Some title2")

    def test_output_string(self):
        jdx_link = CompoundJDX("test")
        jdx_block = SimpleJDX(
            title="Some title", data_type="IR", xypoints=[[1, 2, 3], [4, 5, 6]]
        )
        jdx_block2 = SimpleJDX(
            title="Some title2", data_type="IR", xydata=[[1, 2, 3], [4, 5, 6]]
        )
        jdx_link.add_block(jdx_block)
        jdx_link.add_block(jdx_block2)

        output_string = jdx_link.to_string()

        self.assertEqual(
            output_string,
            f"""##TITLE= test
##JCAMP-DX= 5.01
##DATA TYPE= LINK
##BLOCKS= 2

{jdx_block.__repr__()}

{jdx_block2.__repr__()}

##END=""",
        )
