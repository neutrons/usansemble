"""Tests for the ``MeasurementType`` mirror of ``usansred.enums.MeasurementType``.

The expected names and values are written out literally, so any edit to the
mirror is caught. Once ``usansred`` is importable, these assertions become an
equality check against ``usansred``'s own enum.
"""

from usansemble.enums import ROLE_LABELS, MeasurementType


def test_measurement_type_members() -> None:
    assert [(member.name, member.value) for member in MeasurementType] == [
        ("SAMPLE", "sample"),
        ("BACKGROUND", "background"),
        ("EMPTY_CELL", "empty_cell"),
    ]


def test_measurement_type_is_a_str() -> None:
    # StrEnum members compare and format as their raw value, which is what
    # usansred writes to and reads from the JSON configuration.
    assert MeasurementType.EMPTY_CELL == "empty_cell"
    assert str(MeasurementType.EMPTY_CELL) == "empty_cell"
    assert MeasurementType("background") is MeasurementType.BACKGROUND


def test_role_labels_cover_every_member() -> None:
    assert list(ROLE_LABELS) == list(MeasurementType)
    assert ROLE_LABELS[MeasurementType.SAMPLE] == "sample"
    assert ROLE_LABELS[MeasurementType.BACKGROUND] == "background"
    assert ROLE_LABELS[MeasurementType.EMPTY_CELL] == "empty cell"
