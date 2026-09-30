"""The role assignment model behind the role table.

A :class:`RoleCast` holds one :class:`RunAssignment` per fetched run, recording
the role that run plays in the reduction (sample, background or empty cell).
It is pure data with no NiceGUI calls, so it is unit-testable without a UI
context, in the same spirit as pyoncatng's ``RunTable.build_options``.

Validation is limited to run-number lookup: ``usansred.ReductionConfig`` will
own validation once ``usansred`` becomes a dependency, so nothing here
anticipates it.
"""

import copy
from collections.abc import Iterable, Sequence
from dataclasses import dataclass

from pyoncatng.widgets.iptstable import KEY_COLUMN as ID_COLUMN
from pyoncatng.widgets.iptstable import Row

from usansemble.enums import ROLE_LABELS, MeasurementType

# The column of a ``RunsSelector`` row that seeds a run's name. It must match
# ``runs_selector.TITLE_COLUMN``; it is repeated here so the model does not
# import the login widget, and a test checks that the two agree.
TITLE_COLUMN = "Title"

# Keys of the rows emitted by :meth:`RoleCast.as_rows`. ``ROLE_VALUE_KEY`` has
# no matching grid column: it carries the raw enum value for the row-coloring
# rules, which then do not depend on the display label.
NAME_COLUMN = "Name"
ROLE_COLUMN = "Role"
THICKNESS_COLUMN = "Thickness"
TRANSMISSION_COLUMN = "Transmission"
ROLE_VALUE_KEY = "_role"


@dataclass
class RunAssignment:
    """The role of one run, with the per-run values a reduction needs."""

    run_number: int
    name: str
    role: MeasurementType = MeasurementType.SAMPLE
    thickness: float | None = None
    transmission: float | None = None


class RoleCast:
    """The role assignments of the fetched runs, keyed by run number.

    Assignments keep the order the runs were given to :meth:`set_runs`.
    """

    def __init__(self) -> None:
        self._assignments: dict[int, RunAssignment] = {}

    @property
    def assignments(self) -> list[RunAssignment]:
        """Deep copies of the assignments, in run order."""
        return copy.deepcopy(list(self._assignments.values()))

    def set_runs(self, rows: Sequence[Row]) -> None:
        """Replace the runs with those in ``rows``, keeping existing assignments.

        A run already present keeps its assignment unchanged. A new run is
        named after its ``Title`` and starts as a sample. A run missing from
        ``rows`` is dropped. ``int`` makes a run number reported as a string
        match the same run reported as an integer.
        """
        assignments: dict[int, RunAssignment] = {}
        for row in rows:
            run_number = int(row[ID_COLUMN])
            existing = self._assignments.get(run_number)
            if existing is None:
                existing = RunAssignment(run_number=run_number, name=str(row.get(TITLE_COLUMN) or ""))
            assignments[run_number] = existing
        self._assignments = assignments

    def assign(self, run_numbers: Iterable[int], role: MeasurementType) -> None:
        """Give every run in ``run_numbers`` the given role.

        Raises
        ------
        KeyError
            If a run number is not present. Every run number is looked up
            before any role changes, so a failed call leaves all roles as they
            were.
        """
        targets = [self._assignments[int(run_number)] for run_number in run_numbers]
        for assignment in targets:
            assignment.role = role

    def as_rows(self) -> list[Row]:
        """Project the assignments into grid rows, in run order."""
        return [
            {
                ID_COLUMN: assignment.run_number,
                NAME_COLUMN: assignment.name,
                ROLE_COLUMN: ROLE_LABELS[assignment.role],
                THICKNESS_COLUMN: assignment.thickness,
                TRANSMISSION_COLUMN: assignment.transmission,
                ROLE_VALUE_KEY: assignment.role.value,
            }
            for assignment in self._assignments.values()
        ]
