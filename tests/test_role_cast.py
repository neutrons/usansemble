"""Tests for the ``RoleCast`` role assignment model.

The model has no NiceGUI calls, so these tests need no ``user`` fixture. Input
rows have the shape ``RunsSelector`` hands to ``on_runs_fetched`` callbacks.
"""

import pytest

from usansemble import role_cast
from usansemble.enums import MeasurementType
from usansemble.role_cast import RoleCast, RunAssignment
from usansemble.widgets import runs_selector


def _row(run_id, title: str = "Align:500 10min cure with SI") -> dict:
    """A fetched row as ``RunsSelector`` emits it."""
    return {
        "ID": run_id,
        "Title": title,
        "Start Time": "2020-11-23T20:31:23.874765-05:00",
        "Total Counts": 261607,
    }


def _cast(*run_ids: int) -> RoleCast:
    cast = RoleCast()
    cast.set_runs([_row(run_id, title=f"title {run_id}") for run_id in run_ids])
    return cast


def _roles(cast: RoleCast) -> dict[int, MeasurementType]:
    return {assignment.run_number: assignment.role for assignment in cast.assignments}


def test_columns_agree_with_runs_selector() -> None:
    assert role_cast.ID_COLUMN == runs_selector.ID_COLUMN
    assert role_cast.TITLE_COLUMN == runs_selector.TITLE_COLUMN


def test_new_cast_is_empty() -> None:
    cast = RoleCast()
    assert cast.assignments == []
    assert cast.as_rows() == []


def test_set_runs_seeds_samples_from_titles() -> None:
    cast = RoleCast()
    cast.set_runs([_row(33221, title="Align:0 stop rheometer")])

    assert cast.assignments == [
        RunAssignment(
            run_number=33221,
            name="Align:0 stop rheometer",
            role=MeasurementType.SAMPLE,
            thickness=None,
            transmission=None,
        )
    ]


def test_set_runs_without_a_title_gives_an_empty_name() -> None:
    cast = RoleCast()
    cast.set_runs([{"ID": 1}, {"ID": 2, "Title": None}])
    assert [assignment.name for assignment in cast.assignments] == ["", ""]


def test_set_runs_keeps_the_given_order() -> None:
    cast = _cast(30, 10, 20)
    assert [assignment.run_number for assignment in cast.assignments] == [30, 10, 20]


def test_assign_overwrites_and_returns_to_sample() -> None:
    cast = _cast(1, 2, 3)

    cast.assign([2, 3], MeasurementType.BACKGROUND)
    cast.assign([3], MeasurementType.EMPTY_CELL)
    assert _roles(cast) == {
        1: MeasurementType.SAMPLE,
        2: MeasurementType.BACKGROUND,
        3: MeasurementType.EMPTY_CELL,
    }

    cast.assign([2, 3], MeasurementType.SAMPLE)
    assert set(_roles(cast).values()) == {MeasurementType.SAMPLE}


def test_assign_accepts_any_iterable() -> None:
    cast = _cast(1, 2)
    cast.assign((n for n in [1, 2]), MeasurementType.BACKGROUND)
    assert set(_roles(cast).values()) == {MeasurementType.BACKGROUND}


def test_assign_nothing_changes_nothing() -> None:
    cast = _cast(1)
    cast.assign([], MeasurementType.BACKGROUND)
    assert _roles(cast) == {1: MeasurementType.SAMPLE}


def test_assign_unknown_run_raises_and_changes_nothing() -> None:
    cast = _cast(1, 2)

    with pytest.raises(KeyError, match="99"):
        cast.assign([1, 99, 2], MeasurementType.BACKGROUND)

    assert _roles(cast) == {1: MeasurementType.SAMPLE, 2: MeasurementType.SAMPLE}


def test_as_rows_projects_assignments() -> None:
    cast = _cast(2, 1)
    cast.assign([1], MeasurementType.EMPTY_CELL)

    assert cast.as_rows() == [
        {
            "ID": 2,
            "Name": "title 2",
            "Role": "sample",
            "Thickness": None,
            "Transmission": None,
            "_role": "sample",
        },
        {
            "ID": 1,
            "Name": "title 1",
            "Role": "empty cell",
            "Thickness": None,
            "Transmission": None,
            "_role": "empty_cell",
        },
    ]


def test_set_runs_again_keeps_roles_of_runs_still_present() -> None:
    cast = _cast(1, 2, 3)
    cast.assign([2], MeasurementType.BACKGROUND)
    cast.assign([3], MeasurementType.EMPTY_CELL)

    cast.set_runs([_row(2), _row(3), _row(4)])

    assert _roles(cast) == {
        2: MeasurementType.BACKGROUND,
        3: MeasurementType.EMPTY_CELL,
        4: MeasurementType.SAMPLE,
    }


def test_set_runs_again_keeps_the_existing_name() -> None:
    cast = RoleCast()
    cast.set_runs([_row(1, title="first")])
    cast.set_runs([_row(1, title="retitled")])
    assert cast.assignments[0].name == "first"


def test_run_numbers_given_as_strings_match_integers() -> None:
    cast = RoleCast()
    cast.set_runs([_row("33221")])
    cast.assign(["33221"], MeasurementType.BACKGROUND)
    cast.set_runs([_row(33221)])

    assert _roles(cast) == {33221: MeasurementType.BACKGROUND}
    assert cast.as_rows()[0]["ID"] == 33221


def test_assignments_are_copies() -> None:
    cast = _cast(1)
    cast.assignments[0].role = MeasurementType.BACKGROUND
    assert _roles(cast) == {1: MeasurementType.SAMPLE}


def test_as_rows_are_copies() -> None:
    cast = _cast(1)
    cast.as_rows()[0]["_role"] = "background"
    assert cast.as_rows()[0]["_role"] == "sample"
