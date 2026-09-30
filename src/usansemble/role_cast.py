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

    Assignments are ordered by decreasing run number, the order in which the
    ``IPTSTable`` of ``RunsSelector`` lists the runs, whatever order
    :meth:`add_runs` receives them in. Runs are added by :meth:`add_runs` and
    leave only through :meth:`remove`.

    Runs sharing a name belong to one USANS measurement, so they always share a
    role: :meth:`assign` sets the role of whole name groups, and a newly fetched
    run takes the role of the runs with its name already in the cast. Names are compared exactly, as the
    title double-click of ``RunsSelector`` compares titles.
    """

    def __init__(self) -> None:
        self._assignments: dict[int, RunAssignment] = {}

    @property
    def assignments(self) -> list[RunAssignment]:
        """Deep copies of the assignments, by decreasing run number."""
        return copy.deepcopy(list(self._assignments.values()))

    def add_runs(self, rows: Sequence[Row]) -> list[int]:
        """Add the runs in ``rows`` that are not in the cast yet.

        A run already present keeps its assignment unchanged, and no run is
        dropped. A new run is named after its ``Title`` and takes the role of
        the runs with the same name already in the cast, or starts as a sample
        if there are none. ``int`` makes a run number reported as a string
        match the same run reported as an integer, and keeps the ordering
        numeric.

        Returns
        -------
        list of int
            The run numbers added, by decreasing run number.
        """
        # Runs sharing a name share a role, so any run of a group gives it.
        group_roles = {assignment.name: assignment.role for assignment in self._assignments.values()}
        assignments = dict(self._assignments)
        added: list[int] = []
        for row in rows:
            run_number = int(row[ID_COLUMN])
            if run_number in assignments:
                continue
            name = str(row.get(TITLE_COLUMN) or "")
            role = group_roles.get(name, MeasurementType.SAMPLE)
            assignments[run_number] = RunAssignment(run_number=run_number, name=name, role=role)
            added.append(run_number)
        self._assignments = dict(sorted(assignments.items(), reverse=True))
        return sorted(added, reverse=True)

    def remove(self, run_numbers: Iterable[int]) -> list[int]:
        """Remove the runs in ``run_numbers``, and only those.

        Other runs sharing a name with a removed run stay, with their role.

        Returns
        -------
        list of int
            The run numbers removed, by decreasing run number.

        Raises
        ------
        KeyError
            If a run number is not present. Every run number is looked up
            before any run is removed, so a failed call removes nothing.
        """
        targets = {self._assignments[int(run_number)].run_number for run_number in run_numbers}
        self._assignments = {n: a for n, a in self._assignments.items() if n not in targets}
        return sorted(targets, reverse=True)

    def assign(self, run_numbers: Iterable[int], role: MeasurementType) -> list[int]:
        """Give ``role`` to every run sharing a name with a run in ``run_numbers``.

        Selecting any one run of a measurement therefore assigns the role to the
        whole measurement.

        Returns
        -------
        list of int
            The run numbers whose role was set, by decreasing run number.

        Raises
        ------
        KeyError
            If a run number is not present. Every run number is looked up
            before any role changes, so a failed call leaves all roles as they
            were.
        """
        names = {self._assignments[int(run_number)].name for run_number in run_numbers}
        targets = [assignment for assignment in self._assignments.values() if assignment.name in names]
        for assignment in targets:
            assignment.role = role
        return [assignment.run_number for assignment in targets]

    def as_rows(self) -> list[Row]:
        """Project the assignments into grid rows, by decreasing run number."""
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
