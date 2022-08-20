import json
import warnings
from copy import copy
from typing import Any, Dict, List

from .data_records import (
    AFFNDataRecord,
    DataRecord,
    LongDateDataRecord,
    StringDataRecord,
    TextDataRecord,
)
from .data_table_records import (
    DataTableRecord,
    SequenceDataTableRecord,
    TupleDataTableRecord,
)


class BaseJDX:
    """Common class for simple and compound JDX files"""

    # List of data records to put in output
    output_data_records = None

    def __init__(self, *args, **kwargs) -> None:
        # Copy class attributes to the instance attribute
        # This is to avoid affection of different instances by changing value in
        # only one of them
        all_data_records = self._all_data_records() + self._all_data_table_records()
        for name in all_data_records:
            setattr(self, name, copy(getattr(self.__class__, name)))
        setattr(self, "output_data_records", copy(self.output_data_records))

    def _all_data_records(self) -> List[str]:
        """Get list of all data records in the class

        Returns
        -------
        List[str]
            List of data records of the class, i.e. ['title', 'jcamp_dx', ...]
        """
        data_record_attrs = [
            dr for dr in self.__dir__() if isinstance(getattr(self, dr), DataRecord)
        ]

        try:
            i0 = data_record_attrs.index("title")
        except ValueError:
            raise AssertionError(
                "'title' is not presented in the list of data records of the class"
            )

        # If there were some user-defined records before 'title', move them to the end
        if i0 != 0:
            data_record_attrs = data_record_attrs[i0:] + data_record_attrs[:i0]

        return data_record_attrs

    def _all_data_table_records(self) -> List[str]:
        """Get list of all data table records in the class

        Returns
        -------
        List[str]
            List of data table records of the class, i.e. ['xydata', 'xypoints', ...]
        """
        return [
            dr
            for dr in self.__dir__()
            if isinstance(getattr(self, dr), DataTableRecord)
        ]

    def get_output_data_records(self) -> List[str]:
        """Get data records attributes for final output

        Get list of all data record attributes that should be presented in the final
        output. By default, validates and returns `self.output_data_records` attribute
        If it is not provided (i.e. None), then returns a list containing only required
        data records and data records with non-empty values.
        """
        all_data_records = self._all_data_records()
        if self.output_data_records is None:
            data_records_attrs = [
                name
                for name in all_data_records
                if getattr(self, name).required or bool(getattr(self, name).value)
            ]
        else:
            # Check that all listed LDRs are defined
            for dr in self.output_data_records:
                if dr not in all_data_records:
                    raise AssertionError(
                        f"Data record '{dr}' in 'output_data_records' was not defined"
                    )
            # Check that all required LDRs are there
            for dr in all_data_records:
                if (getattr(self, dr).required) and (
                    dr not in self.output_data_records
                ):
                    raise AssertionError(
                        f"Data record '{dr}' is required by not included in 'output_data_records'"
                    )

            data_records_attrs = self.output_data_records

        if data_records_attrs[0] != "title":
            raise AssertionError("First output data record must be 'title'")

        return data_records_attrs

    def values_dict(self) -> Dict[str, Any]:
        """Convert to dict of values

        Returns
        -------
        Dict[str, Any]
            A dictionary where the keys are the data record and data table record
            attributes; and the dict-values are the values of those attributes.
        """
        # Get all data record values
        values_dict = {
            name: getattr(self, name).value for name in self._all_data_records()
        }

        return values_dict

    def validate(self) -> Dict[str, List[str]]:
        """Validate all values

        Returns
        -------
        Dict[str, List[str]]
            Dictionary of found errors. The key is the name of the data record
            attribute with the validation error(s). The value is the list of found
            validation errors. Therefore, in case of valid data, returns an empty
            dictionary
        """
        # Get dict of values
        values_dict = self.values_dict

        # Run all data record validators
        validations = {
            name: getattr(self, name).validate(values_dict)
            for name in self.get_output_data_records()
        }

        # Remove empty ([]) validations
        validations = {k: v for k, v in validations.items() if len(v)}

        return validations

    def to_string(self, **kwargs) -> str:
        """Validate and convert to a string"""
        # Validate the values
        validations = self.validate()
        if len(validations):
            warnings.warn(json.dumps(validations, indent=4))

        return self.__repr__()

    def to_file(self, filepath: str, **kwargs) -> None:
        """Write to JDX file"""
        with open(filepath, "w") as f:
            f.write(self.to_string(**kwargs))

    def __str__(self) -> str:
        """Convert to a shorter string"""
        output_records = [
            str(getattr(self, name)) for name in self.get_output_data_records()
        ]
        return "\n".join(output_records)

    def __repr__(self) -> str:
        """Convert to a final output string"""
        output_records = [
            repr(getattr(self, name)) for name in self.get_output_data_records()
        ]
        return "\n".join(output_records)


class SimpleJDX(BaseJDX):
    """Single-block JDX data

    The base class for simple JDX, i.e. contains actual spectral data and does not
    have inner blocks. The class is based on the description of verion 5.01 of the
    JCAMP-DX specification.
    This class contains general data records unspecific to data type. For a specific
    data type one can create a corresponding subclass
    """

    # Header
    title = TextDataRecord(
        label="TITLE",
        required=True,
        description="Should contain a concise description of the spectrum, suitable as a title for a plotted spectrum.",
    )
    jcamp_dx = StringDataRecord(label="JCAMP-DX", choices=["5.01"], required=True)
    data_type = StringDataRecord(
        label="DATA TYPE",
        choices=[
            "INFRARED SPECTRUM",
            "RAMAN SPECTRUM",
            "INFRARED PEAK TABLE",
            "INFRARED INTERFEROGRAM",
            "INFRARED TRANSFORMED SPECTRUM",
        ],
        required=True,
    )

    # SPECTRAL PARAMETERS
    xunits = StringDataRecord(
        label="XUNITS",
        choices=["l/CM", "MICROMETERS", "NANOMETERS", "SECONDS"],
        required=True,
    )
    yunits = StringDataRecord(
        label="YUNITS",
        choices=[
            "TRANSMITTANCE",
            "REFLECTANCE",
            "ABSORBANCE",
            "KUBELKA-MUNK",
            "ARBITRARY UNITS",
        ],
        required=True,
    )
    firstx = AFFNDataRecord(
        label="FIRSTX", required=True, description="First actual abscissa value"
    )
    lastx = AFFNDataRecord(
        label="LASTX", required=True, description="Last actual abscissa value"
    )
    maxx = AFFNDataRecord(label="MAXX")
    minx = AFFNDataRecord(label="MINX")
    maxy = AFFNDataRecord(label="MAXY")
    miny = AFFNDataRecord(label="MINY")
    xfactor = AFFNDataRecord(label="XFACTOR", required=True)
    yfactor = AFFNDataRecord(label="YFACTOR", required=True)
    npoints = AFFNDataRecord(
        label="NPOINTS", required=True, description="Number of components in the data"
    )
    firsty = AFFNDataRecord(label="FIRSTY")
    resolution = StringDataRecord(
        label="RESOLUTION",
        required=False,
        description="Nominal resolution in units specified by ##XUNITS=, as a single number for spectra at constant resolution throughout, or as pairs of the form: R,,X,; . . . ;Ri,Xi, where Ri stands for resolution at abscissa Xi. ##RESOLUTION= is strongly recommended for FT-IR spectra.",
    )
    deltax = DataRecord(
        label="DELTAX",
        format="AFFN|ASDF",
        required=False,
        description="The nominal spacing between points for inspection by the user.",
    )
    xlabel = TextDataRecord(label="XLABEL")
    ylabel = TextDataRecord(label="YLABEL")

    # TABULAR SPECTRA DATA
    xydata = SequenceDataTableRecord("XYDATA", "(X++(Y..Y))")
    xypoints = TupleDataTableRecord("XYPOINTS", "(XY..XY)")
    peak_table = TupleDataTableRecord("PEAK TABLE", "(XY..XY)")

    # JCAMP-DX RESERVED LABELS FOR NOTES
    class_ = StringDataRecord(
        label="CLASS",
        required=False,
        description="Specifies the Coblentz Class and the IUPAC Class of digital representation. This LDR is required for spectra of pure compounds. ",
    )
    origin = TextDataRecord(
        label="ORIGIN",
        required=True,
        description="Name of organization, address, telephone number, name of individual contrib- utor, etc., as appropriate.",
    )
    owner = TextDataRecord(
        label="OWNER",
        required=True,
        description="Name of owner of a proprietary spectrum. The organization or person named under ##ORIGIN= is responsible for accuracy of this field. If data are copyrighted, this line should read “COPYRIGHT (C) (year) by (name).”",
    )
    long_date = LongDateDataRecord(
        label="LONG DATE",
        required=False,
        description="Date when the spectrum was measured in the form: YYYY/MM/DD HH:MM:SS.SSSS ±UUUU",
    )
    source_reference = TextDataRecord(
        label="SOURCE REFERENCE",
        required=False,
        description="Adequate identification to locate the original spectrum, i.e., name of file containing the spectrum, or library name and serial number of the spectrum.",
    )
    cross_reference = TextDataRecord(
        label="CROSS REFERENCE",
        required=False,
        description="Cross references refer to additional spectra of the same sample, i.e., different thickness, mulling agent, polarization, temperature, time, etc., or serve to link a peak table or in- terferogram with a spectrum.",
    )

    # SAMPLE INFORMATION
    sample_description = TextDataRecord(
        label="SAMPLE DESCRIPTION",
        required=False,
        description="If the sample is not a pure compound, this field should contain its description, i.e., composition, origin, appearance, re- sults of interpretation, etc. If the sample is a known compound, the following LDRs specify structure and properties, as appropriate.",
    )
    iupac_name = TextDataRecord(
        label="IUPAC NAME",
        description="The use of IUPAC names has been recommended previously by the Commission on Molecular Structure and Spectroscopy of the Physical Chemistry Division in 1991",
    )
    cas_name = StringDataRecord(
        label="CAS NAME",
        description="Name according to Chemical Abstracts naming conventions as described in Appendix IV of the 1985 CAS Index Guide. Examples can be found in Chemical Abstracts indices or the Merck Index. Greek letters are spelled out, and standard ASCII capitals are used for small capitals. Sub-/superscripts are indicated by prefixes / and /\\, respectively. Example: alpha-D-glucopyranose, 1-(dihydrogen phosphate).",
    )
    names = StringDataRecord(label="NAMES")
    molform = StringDataRecord(label="MOLFORM")
    cas_registry_no = StringDataRecord(label="CAS REGISTRY NO")
    wiswesser = StringDataRecord(label="WISWESSER")
    beilstein_lawson_no = StringDataRecord(label="BEILSTEIN LAWSON NO")
    mp = AFFNDataRecord(label="MP")
    bp = AFFNDataRecord(label="BP")
    refractive_index = AFFNDataRecord(label="REFRACTIVE INDEX")
    density = AFFNDataRecord(label="DENSITY")
    mw = AFFNDataRecord(label="MW")
    concentrations = StringDataRecord(label="CONCENTRATIONS")

    # EQUIPMENT
    spectrometer = StringDataRecord(label="SPECTROMETER/DATA SYSTEM")
    instrument_parameters = StringDataRecord(label="INSTRUMENT PARAMETERS")

    # SAMPLING INFORMATION
    sampling_procedure = TextDataRecord(label="SAMPLING PROCEDURE")
    state = StringDataRecord(label="STATE")
    path_length = StringDataRecord(label="PATH LENGTH")
    pressure = StringDataRecord(label="PRESSURE")
    temperature = StringDataRecord(label="TEMPERATURE")
    data_processing = TextDataRecord(label="DATA PROCESSING")
    audit_trail = DataRecord(
        label="AUDIT TRAIL", format="(AFFN, STRING, TEXT, TEXT, TEXT)"
    )

    # COMMENTS
    comments = TextDataRecord("")

    def __init__(self, single_column=True, decimal_places=4, **kwargs) -> None:
        """Create an instance of a single JDX

        Parameters
        ----------
        single_column : bool, optional
            Should the output data be in single column format, by default True
        decimal_places : int, optional
            How many decimal places to keep, by default 4

        Raises
        ------
        ValueError
            There are more than one data table records
        ValueError
            Unspecified data record provided
        ValueError
            No data table record provided
        NotImplementedError
            Scaling x and y values by xfactor and yfactor is not implemented yet
        """
        super().__init__(**kwargs)
        kwargs.update({"jcamp_dx": "5.01"})

        all_data_records = self._all_data_records()
        data_table_records = self._all_data_table_records()

        # Validate output data records
        self.get_output_data_records()

        _any_data = False
        for k, v in kwargs.items():
            if k in all_data_records:
                # Update meta information
                dr = getattr(self, k)
                dr.value = v
            elif k in data_table_records:
                if _any_data:
                    raise ValueError("Only one data table record is allowed.")

                # Load tabular data information
                self._data_table_record_name: str = k
                self._data_table_record: DataTableRecord = getattr(self, k)
                self._data_table_record.data = v
                self._data_table_record.single_column = single_column
                self._data_table_record.decimal_places = decimal_places
                _any_data = True
            else:
                raise ValueError(f"Unexpected data label {k}")

        if not _any_data:
            raise ValueError("No actual data is provided.")

        # Set data records related to the data
        x = self._data_table_record.data[0]
        self.firstx.value = kwargs.get("firstx", x[0])
        self.lastx.value = kwargs.get("lastx", x[-1])
        self.npoints.value = kwargs.get("npoints", len(x))

        if ("xfactor" in kwargs) or ("yfactor" in kwargs):
            raise NotImplementedError("Custom X/Y factors are not available yet.")
        self.xfactor.value = 1
        self.yfactor.value = 1

    def values_dict(self) -> Dict[str, Any]:
        """Get values dict"""
        # Get all data record values
        values_dict = super().values_dict()
        # Add data table record value
        values_dict.update({self._data_table_record_name: self._data_table_record.data})

        return values_dict

    def validate(self) -> Dict[str, List[str]]:
        """Validate all data records and the data table record"""
        validations = super().validate()

        # Check the data table record
        if self._data_table_record.data is None:
            validations.update({self._data_table_record_name: ["No data provided"]})

        return validations

    def __str__(self) -> str:
        headers = super().__str__()
        return "\n".join([headers, str(self._data_table_record), "##END="])

    def __repr__(self) -> str:
        headers = super().__repr__()
        return "\n".join([headers, repr(self._data_table_record), "##END="])


class CompoundJDX(BaseJDX):
    """Compound (i.e. multi-block) JDX"""

    title = TextDataRecord(label="TITLE", required=True)
    jcamp_dx = StringDataRecord(label="JCAMP-DX", choices=["5.01"], required=True)
    data_type = StringDataRecord(label="DATA TYPE", choices=["LINK"], required=True)
    block_count = AFFNDataRecord(label="BLOCKS", required=True)

    def __init__(self, title: str, *blocks) -> None:
        super().__init__()
        self.jcamp_dx.value = "5.01"
        self.data_type.value = "LINK"
        self.title.value = title
        self.block_count.value = len(blocks)
        self.blocks = list(blocks)

    def add_block(self, block: SimpleJDX) -> None:
        """Append a block with simple JDX

        Raises
        ------
        ValueError
            The block must be a SimpleJDX instance
        """
        if isinstance(block, SimpleJDX):
            self.blocks.append(block)
            self.block_count.value = len(self.blocks)
        else:
            raise ValueError(
                "The inner block must be an instance of a SimpleJDX or its subclass."
            )

    @property
    def nblocks(self) -> int:
        """Get number of blocks"""
        return len(getattr(self, "blocks", []))

    def __str__(self) -> str:
        headers = super().__str__()
        blocks = [str(block) for block in self.blocks]
        self.block_count.value = len(blocks)
        return "\n\n".join([headers, *blocks, "##END="])

    def __repr__(self) -> str:
        headers = super().__repr__()
        blocks = [repr(block) for block in self.blocks]
        self.block_count.value = len(blocks)
        return "\n\n".join([headers, *blocks, "##END="])
