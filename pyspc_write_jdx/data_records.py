from datetime import datetime
from textwrap import wrap
from typing import Any, Callable, Dict, List, Optional, Union


class ValidationError(Exception):
    """An error while validating data."""


def _validate_required(instance: "DataRecord", *args, **kwargs) -> bool:
    """Validate that required data is not missing"""
    if instance.value is None:
        raise ValidationError(f"DATA-LABEL '##{instance.label}=' is required.")
    return True


def _validate_choices(instance: "DataRecord", *args, **kwargs) -> bool:
    """Validate that provided value is one of the allowed choices"""
    if (
        (instance.choices is not None)
        and (instance.value is not None)
        and (instance.value not in instance.choices)
    ):
        raise ValidationError(
            f"Unexpected value for DATA-LABEL '##{instance.label}='. "
            f"Available values {instance.choices}."
        )
    return True


def _validate_date(instance: "DataRecord", *args, **kwargs) -> bool:
    allowed_formats = [
        "%Y/%m/%d",
        "%Y/%m/%d %H:%M",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d %H:%M:%S.%f",
        "%Y/%m/%d %H:%M:%S.%f%z",
    ]
    for format in allowed_formats:
        try:
            datetime.datetime.strptime(instance.value, format)
        except Exception:
            pass
        else:
            return True
    raise ValidationError(
        f"Unexpected date-time format. Allowed formats: {allowed_formats}"
    )


class DataRecord:
    """Generic class for Labeled-Data-Records (LDR)

    This class provides generic interface for all types of LDR
    except spectral data LDR, e.g. XYDATA, XYPOINTS
    """

    def __init__(
        self,
        label: str,
        format: str,
        choices: Optional[List[str]] = None,
        description: Optional[str] = None,
        validators: Optional[List[Callable[[Any, Dict], bool]]] = None,
        required: bool = False,
        comment: Optional[str] = None,
    ) -> None:
        """Initialize Data Record

        Parameters
        ----------
        label : str
            The label that will be printed out. Without '##' and '='. I.e. "TITLE" for
            the value of the "##TITLE=" LDR.
        format : str
            The format provided in the specification:

            * 'TEXT' - data-sets contain descriptive information for humans, not
              normally intended to be parsed by computer, i.e., title, comments, etc.

            * 'STRING' - data-sets contain alphanumeric fields intended to be parsed by
              computer and read by a human. The form of each string field is specified
              under the LDR in which it is used.

            * 'AFFN' (ASCII FREE FORMAT NUMERIC) - a field which starts with a
              +, -, decimal point, or digit is treated as a numeric field and converted
              to the internal form of the target computer. E is the only other allowed
              character. A numeric field is terminated by E, comma, or blank. If E is
              followed immediately by either + or - and a two- or three-digit integer,
              it gives the power of 10 by which the initial field must be multiplied.

            * 'ASDF' (ASCII SQUEEZED DIFFERENCE FORM) - a special form for compressing
              tabular spectral data described in Section 5 of the format specification.

            * 'AFFN|ASDF' - either one of AFFN or ASDF
        choices : Optional[List[str]], optional
            List of allowed values, by default None
        description : Optional[str], optional
            Description of the LDR from the specification, by default None
        validators : Optional[List[Callable[[Any, Dict], bool]]], optional
            List of callables that would either return True if the DATA-SET of the LDR
            is valid and corresponds to the specification; otherwise raise a validation
            error. The callable should accept two arguments: one the instance of
            the DataRecord class, the second - the dict of other LDR values from the
            corresponding BLOK. By default None.
        required : bool, optional
            Is the LDR required, by default False
        comment : Optional[str], optional
            Comment on the LDR, by default None. This will be added as an inline comment
            after '$$'.
        """
        self.label = label
        self.format = format
        self.choices = choices
        self.description = description
        self._required = required
        self._value = None
        self.comment = comment

        # Prepare validators
        if validators is None:
            validators = []

        if self.choices is not None:
            validators = [_validate_choices, *validators]

        if self._required:
            validators = [_validate_required, *validators]

        self.validators = validators

    @property
    def required(self):
        return self._required

    # Generic interface to work with LDR values/DATA-SET.  This is need to allow
    # pre-processing of values for some LDR, e.g. LONG_DATE
    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value):
        self._value = value

    @value.deleter
    def value(self):
        del self._value

    def validate(self, block_values: Dict[str, Any]) -> List[str]:
        """Validate LDR value

        Parameters
        ----------
        block_values : Dict[str, Any]
            Dictionary of all LDRs (<DATA-LABEL>:<DATA-SET>) in the corresponding BLOCK
            of the JDX. Since some validation rules are based on the context of the JDX
            (e.g. DATA TYPE), we provide all the context.

        Returns
        -------
        List[str]
            List of validation errors
        """
        errors = []
        for validator in self.validators:
            try:
                validator(self, block_values)
            except Exception as e:
                errors.append(str(e))

        return errors

    def __str__(self) -> str:
        """Convert DATA-RECORD to a corresponding LINES in JDX format"""
        ldr = f"##{self.label}="

        # Wrap lines by 80 symbols
        if self.value is not None:
            ldr = wrap(f"{ldr} {self.value}", width=80)
        else:
            ldr = [ldr]

        # Add an inline comment if provided
        if self.comment is not None:
            ldr[0] = f"{ldr[0]}  $$ {self.comment}"
        return "\n".join(ldr)

    def __repr__(self) -> str:
        return self.__str__()


class TextDataRecord(DataRecord):
    """Wraper class for TEXT LDRs"""

    def __init__(self, label: str, **kwargs) -> None:
        super().__init__(label, "TEXT", choices=None, **kwargs)


class StringDataRecord(DataRecord):
    """Wraper class for STRING LDRs"""

    def __init__(self, label: str, **kwargs) -> None:
        super().__init__(label, "STRING", **kwargs)


class AFFNDataRecord(DataRecord):
    """Wraper class for AFFN LDRs"""

    def __init__(self, label: str, **kwargs) -> None:
        super().__init__(label, "AFFN", choices=None, **kwargs)


class LongDateDataRecord(DataRecord):
    """Wraper class for the LONG_DATE LDR"""

    def __init__(self, label, **kwargs) -> None:
        # Add date validator
        validators = kwargs.get("validators", [])
        validators.append(_validate_date)

        super().__init__(
            label=label,
            format="STRING",
            choices=None,
            **kwargs,
        )

    @property
    def value(self):
        return self._value

    @value.setter
    def value(self, value: Union[str, datetime]):
        """Conver datetime to string before changing the value"""
        if isinstance(value, datetime):
            self._value = value.strftime("%Y/%m/%d %H:%M:%S.%f%z")
        else:
            self._value = str(value)

    @value.deleter
    def value(self):
        del self._value


class TabularSpectralDataRecord(DataRecord):
    pass
