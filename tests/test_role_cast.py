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
    cast.add_runs([_row(run_id, title=f"title {run_id}") for run_id in run_ids])
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


def test_add_runs_seeds_samples_from_titles() -> None:
    cast = RoleCast()
    cast.add_runs([_row(33221, title="Align:0 stop rheometer")])

    assert cast.assignments == [
        RunAssignment(
            run_number=33221,
            name="Align:0 stop rheometer",
            role=MeasurementType.SAMPLE,
            thickness=None,
            transmission=None,
        )
    ]


def test_add_runs_without_a_title_gives_an_empty_name() -> None:
    cast = RoleCast()
    cast.add_runs([{"ID": 1}, {"ID": 2, "Title": None}])
    assert [assignment.name for assignment in cast.assignments] == ["", ""]


def test_add_runs_orders_by_decreasing_run_number() -> None:
    # The role table lists runs highest first, as the RunsSelector table does,
    # whatever order the caller passes them in.
    cast = _cast(10, 30, 20)
    assert [assignment.run_number for assignment in cast.assignments] == [30, 20, 10]
    assert [row["ID"] for row in cast.as_rows()] == [30, 20, 10]


def test_add_runs_orders_numerically() -> None:
    cast = RoleCast()
    cast.add_runs([_row("9"), _row("10")])
    assert [assignment.run_number for assignment in cast.assignments] == [10, 9]


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


def test_as_rows_projects_assignments() -> None:
    cast = _cast(1, 2)
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


def test_add_runs_again_keeps_every_run_and_its_role() -> None:
    cast = _cast(1, 2, 3)
    cast.assign([2], MeasurementType.BACKGROUND)
    cast.assign([3], MeasurementType.EMPTY_CELL)

    # Run 1 is not in this fetch, but a fetch only adds runs.
    added = cast.add_runs([_row(2), _row(3), _row(4)])

    assert added == [4]
    assert _roles(cast) == {
        4: MeasurementType.SAMPLE,
        3: MeasurementType.EMPTY_CELL,
        2: MeasurementType.BACKGROUND,
        1: MeasurementType.SAMPLE,
    }


def test_add_runs_returns_the_added_runs() -> None:
    cast = RoleCast()
    assert cast.add_runs([_row(1), _row(3), _row(2)]) == [3, 2, 1]
    assert cast.add_runs([_row(2), _row(3)]) == []
    assert cast.add_runs([]) == []


def test_add_runs_again_keeps_the_existing_name() -> None:
    cast = RoleCast()
    cast.add_runs([_row(1, title="first")])
    cast.add_runs([_row(1, title="retitled")])
    assert cast.assignments[0].name == "first"


def test_run_numbers_given_as_strings_match_integers() -> None:
    cast = RoleCast()
    cast.add_runs([_row("33221")])
    cast.assign(["33221"], MeasurementType.BACKGROUND)
    cast.add_runs([_row(33221)])

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


def _measurement_cast() -> RoleCast:
    """Two measurements of three runs each, plus a run with its own name."""
    cast = RoleCast()
    cast.add_runs(
        [_row(n, title="cure") for n in (10, 11, 12)]
        + [_row(n, title="empty") for n in (20, 21, 22)]
        + [_row(30, title="align")]
    )
    return cast


def test_assign_assigns_the_whole_measurement() -> None:
    cast = _measurement_cast()

    assigned = cast.assign([11], MeasurementType.BACKGROUND)

    assert assigned == [12, 11, 10]
    assert _roles(cast) == {
        30: MeasurementType.SAMPLE,
        22: MeasurementType.SAMPLE,
        21: MeasurementType.SAMPLE,
        20: MeasurementType.SAMPLE,
        12: MeasurementType.BACKGROUND,
        11: MeasurementType.BACKGROUND,
        10: MeasurementType.BACKGROUND,
    }


def test_assign_unions_the_selected_names() -> None:
    cast = _measurement_cast()

    assigned = cast.assign([10, 12, 30], MeasurementType.EMPTY_CELL)

    assert assigned == [30, 12, 11, 10]
    assert {n for n, role in _roles(cast).items() if role is MeasurementType.EMPTY_CELL} == {30, 12, 11, 10}


def test_assign_returns_the_measurement_to_sample() -> None:
    cast = _measurement_cast()
    cast.assign([20], MeasurementType.EMPTY_CELL)

    cast.assign([22], MeasurementType.SAMPLE)

    assert set(_roles(cast).values()) == {MeasurementType.SAMPLE}


def test_assign_compares_names_exactly() -> None:
    cast = RoleCast()
    cast.add_runs([_row(1, title="cure"), _row(2, title="Cure"), _row(3, title="cure ")])

    assert cast.assign([1], MeasurementType.BACKGROUND) == [1]


def test_assign_unknown_run_raises_and_changes_nothing() -> None:
    cast = _measurement_cast()

    with pytest.raises(KeyError, match="99"):
        cast.assign([11, 99], MeasurementType.BACKGROUND)

    assert set(_roles(cast).values()) == {MeasurementType.SAMPLE}


def test_assign_nothing_changes_nothing() -> None:
    cast = _measurement_cast()
    assert cast.assign([], MeasurementType.BACKGROUND) == []
    assert set(_roles(cast).values()) == {MeasurementType.SAMPLE}


def test_new_run_takes_the_role_of_its_name_group() -> None:
    # 33219 is fetched later but belongs to the measurement already assigned.
    cast = RoleCast()
    cast.add_runs([_row(n, title="cure") for n in (33215, 33216)] + [_row(33221, title="align")])
    cast.assign([33215], MeasurementType.BACKGROUND)

    cast.add_runs([_row(n, title="cure") for n in (33215, 33216, 33219)] + [_row(33221, title="align")])

    assert _roles(cast) == {
        33221: MeasurementType.SAMPLE,
        33219: MeasurementType.BACKGROUND,
        33216: MeasurementType.BACKGROUND,
        33215: MeasurementType.BACKGROUND,
    }


def test_new_run_takes_the_role_of_its_name_group_outside_the_fetch() -> None:
    cast = RoleCast()
    cast.add_runs([_row(1, title="cure")])
    cast.assign([1], MeasurementType.BACKGROUND)

    # Run 1 is not in this fetch, but it is in the cast, so it gives run 2 its role.
    cast.add_runs([_row(2, title="cure")])

    assert _roles(cast) == {2: MeasurementType.BACKGROUND, 1: MeasurementType.BACKGROUND}


def test_new_run_without_a_name_group_starts_as_a_sample() -> None:
    cast = RoleCast()
    cast.add_runs([_row(1, title="cure")])
    cast.assign([1], MeasurementType.BACKGROUND)

    cast.add_runs([_row(1, title="cure"), _row(2, title="empty")])

    assert _roles(cast) == {2: MeasurementType.SAMPLE, 1: MeasurementType.BACKGROUND}


def test_runs_sharing_a_name_always_share_a_role() -> None:
    cast = _measurement_cast()
    cast.assign([10], MeasurementType.BACKGROUND)
    cast.assign([21], MeasurementType.EMPTY_CELL)
    cast.add_runs(
        [_row(n, title="cure") for n in (11, 12, 13)]
        + [_row(n, title="empty") for n in (22, 23)]
        + [_row(31, title="align")]
    )
    cast.assign([13], MeasurementType.SAMPLE)
    cast.assign([23], MeasurementType.BACKGROUND)

    roles_by_name: dict[str, set] = {}
    for assignment in cast.assignments:
        roles_by_name.setdefault(assignment.name, set()).add(assignment.role)
    assert roles_by_name == {
        "cure": {MeasurementType.SAMPLE},
        "empty": {MeasurementType.BACKGROUND},
        "align": {MeasurementType.SAMPLE},
    }


def test_remove_removes_only_the_given_runs() -> None:
    cast = _measurement_cast()
    cast.assign([10], MeasurementType.BACKGROUND)

    removed = cast.remove([11, 30])

    assert removed == [30, 11]
    # 10 and 12 share 11's name but stay, with their role.
    assert _roles(cast) == {
        22: MeasurementType.SAMPLE,
        21: MeasurementType.SAMPLE,
        20: MeasurementType.SAMPLE,
        12: MeasurementType.BACKGROUND,
        10: MeasurementType.BACKGROUND,
    }


def test_remove_accepts_run_numbers_as_strings() -> None:
    cast = _cast(1, 2)
    assert cast.remove(["2"]) == [2]
    assert list(_roles(cast)) == [1]


def test_remove_unknown_run_raises_and_removes_nothing() -> None:
    cast = _cast(1, 2)

    with pytest.raises(KeyError, match="99"):
        cast.remove([1, 99])

    assert list(_roles(cast)) == [2, 1]


def test_remove_nothing_removes_nothing() -> None:
    cast = _cast(1)
    assert cast.remove([]) == []
    assert list(_roles(cast)) == [1]


def test_removed_run_added_again_rejoins_its_name_group() -> None:
    cast = _measurement_cast()
    cast.assign([10], MeasurementType.EMPTY_CELL)
    cast.remove([11])

    cast.add_runs([_row(11, title="cure")])

    assert _roles(cast)[11] is MeasurementType.EMPTY_CELL


def test_removed_group_added_again_starts_as_a_sample() -> None:
    cast = _measurement_cast()
    cast.assign([10], MeasurementType.EMPTY_CELL)
    cast.remove([10, 11, 12])

    cast.add_runs([_row(10, title="cure")])

    assert _roles(cast)[10] is MeasurementType.SAMPLE
