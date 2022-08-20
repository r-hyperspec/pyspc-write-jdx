"""TABULAR SPECTRAL DATA RECORDS

This module defines data records that represent acutal spectral data
"""
import re
from typing import List


class DataTableRecord:
    def __init__(
        self,
        label: str,
        format: str,
        decimal_places: int = 4,
        comment: str = None,
        single_column: bool = False,
    ) -> None:
        self.label = label
        self.format = format
        self.decimal_places = decimal_places
        self.comment = comment
        self.single_column = single_column
        self._data = None

    @property
    def ndimensions(self) -> int:
        return len(self.dimensions)

    @property
    def data(self):
        return self._data

    @data.setter
    def data(self, data: List[List]):
        if not (isinstance(data, (list, tuple)) and (len(data) == self.ndimensions)):
            raise ValueError(f"The data must be a list of {self.ndimensions} lists")

        if len(set([len(x) for x in data])) != 1:
            raise ValueError("The sub-lists of the data have different size")

        self._data = data

    @data.deleter
    def data(self):
        del self._data

    def _str_first_line(self) -> str:
        """Get firt raw of the spectral data record

        Returns
        -------
        str
            The string for the first line of the data record. For example:
            '#XYDATA= (X++(Y..Y))  $$ some comment'
        """
        first_line = f"##{self.label}= {self.format}"
        if self.comment is not None:
            first_line = f"{first_line}  $$ {self.comment}"
        return first_line

    def _str_single_column_data_lines(self, sep: str = " ") -> List[str]:
        return [
            sep.join([f"{x:.{self.decimal_places}f}" for x in pair])
            for pair in zip(*(self.data))
        ]

    def _str_sequential_data_lines(self) -> List[str]:
        raise NotImplementedError()

    def _str_data_lines(self) -> List[str]:
        if self.single_column:
            return self._str_single_column_data_lines()
        else:
            return self._str_sequential_data_lines()

    def __str__(self) -> str:
        data_lines = self._str_data_lines()
        if len(data_lines) > 3:
            return "\n".join(
                [self._str_first_line(), data_lines[0], "$$etc...", data_lines[-1]]
            )
        else:
            return self.__repr__()

    def __repr__(self) -> str:
        lines = [self._str_first_line()] + self._str_data_lines()
        return "\n".join(lines)


class SequenceDataTableRecord(DataTableRecord):
    def __init__(
        self, label: str, format: str, compression: str = "AFFN", **kwargs
    ) -> None:
        # Parse format
        m = re.match(r"^\(([A-Z])\+\+\(([A-Z])\.\.[A-Z]\)\)$", format)
        if m:
            self.dimensions = list(m.groups())
        else:
            raise ValueError(
                "Unexpected data format. The format must be like '(X++(Y..Y))'"
            )

        # Parse compression
        if compression != "AFFN":
            raise NotImplementedError("Only AFFN (i.e. no compression) is available")
        self.compression = compression

        super().__init__(label, format, **kwargs)


class TupleDataTableRecord(DataTableRecord):
    def __init__(self, label: str, format: str, **kwargs) -> None:
        # Parse format
        m = re.match(r"^\(([A-Z]{2,})\.\.[A-Z]{2,}\)$", format)
        if m:
            self.dimensions = list(m.groups()[0])
        else:
            raise ValueError(
                "Unexpected data format. The format must be like '(XY..XY)'"
            )

        # Load other parameters
        super().__init__(label, format, **kwargs)

    def _str_single_column_data_lines(self) -> List[str]:
        return super()._str_single_column_data_lines(", ")

    def _str_sequential_data_lines(self) -> List[str]:
        # Convert floats to formatted strings
        # This converts all floats to the strings of the same length
        formatted_data = []
        for v in self.data:
            # Format float decimal places
            formatted_v = [f"{x:.{self.decimal_places}f}" for x in v]

            # Pad the values
            max_length = max([len(x) for x in formatted_v])
            formatted_v = [x.rjust(max_length) for x in formatted_v]

            # Add the to list
            formatted_data.append(formatted_v)

        # Generate string pairs/tuples
        # This will give one list
        formatted_pairs = [", ".join(pair) for pair in zip(*formatted_data)]

        # Now we make one long string of tuples/paris
        # and wrap it by 80 characters
        current_line = formatted_pairs[0]
        output_list = []
        sep = " : "
        for pair in formatted_pairs[1:]:
            new_length = len(current_line) + len(pair) + len(sep)
            if new_length > 80:
                output_list.append(current_line)
                current_line = pair
            else:
                current_line = f"{current_line}{sep}{pair}"

        output_list.append(current_line)

        return output_list


class XYDataRecord(SequenceDataTableRecord):
    def __init__(self, **kwargs) -> None:
        super().__init__("XYDATA", "(X++(Y..Y))", **kwargs)


class XYPointsRecord(TupleDataTableRecord):
    def __init__(self, **kwargs) -> None:
        super().__init__("XYPOINTS", "(XY..XY)", **kwargs)
