"""Enumerations shared across usansemble.

:class:`MeasurementType` mirrors ``usansred.enums.MeasurementType`` member for
member and value for value, so a role assigned here serializes to exactly the
string ``usansred`` expects in its reduction configuration.

``usansred`` is not a dependency yet: it pins Python to ``>=3.12,<3.13`` and
pulls ``mantidworkbench`` into what is otherwise a lightweight web app. Once it
is adopted, this mirror is replaced by ``from usansred.enums import
MeasurementType``; ``tests/test_enums.py`` guards the mirror until then.

Display text lives in :data:`ROLE_LABELS` rather than on the enum, so the enum
itself stays identical to ``usansred``'s.
"""

from enum import StrEnum


class MeasurementType(StrEnum):
    """The role a run plays in a USANS reduction."""

    SAMPLE = "sample"
    BACKGROUND = "background"
    EMPTY_CELL = "empty_cell"


# Text shown in the UI for each role.
ROLE_LABELS: dict[MeasurementType, str] = {
    MeasurementType.SAMPLE: "sample",
    MeasurementType.BACKGROUND: "background",
    MeasurementType.EMPTY_CELL: "empty cell",
}
