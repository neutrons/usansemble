"""Tests for the RoleCastTable widget.

The tests use NiceGUI's in-process ``user`` simulation on the ``/roles`` page,
which mounts a bare ``RoleCastTable``; it needs no ONCat agent, so no login is
involved. Rows are fed through ``add_runs`` in the shape ``RunsSelector``
delivers them.
"""

import pytest
from nicegui.testing import User
from pyoncatng.widgets.runtable import RunTable

from usansemble.enums import ROLE_LABELS, MeasurementType
from usansemble.widgets.role_cast_table import (
    ASSIGNED_MESSAGE,
    BACKGROUND_BUTTON_LABEL,
    COLUMNS,
    EMPTY_CELL_BUTTON_LABEL,
    REMOVE_BUTTON_LABEL,
    REMOVED_MESSAGE,
    ROLE_CSS,
    ROLE_ROW_CLASSES,
    ROLE_ROW_COLORS,
    ROW_CLASS,
    SAMPLE_BUTTON_LABEL,
    RoleCastTable,
)


def _widget(user: User) -> RoleCastTable:
    return next(iter(user.find(RoleCastTable).elements))


def _row(run_id: int) -> dict:
    """A fetched row as ``RunsSelector`` emits it."""
    return {
        "ID": run_id,
        "Title": f"title {run_id}",
        "Start Time": "2020-11-23T20:31:23.874765-05:00",
        "Total Counts": 261607,
    }


def _grid_row(run_id: int) -> dict:
    """A role table row, as the selection reads it back from the grid."""
    return {"ID": run_id, "Name": f"title {run_id}", "Role": "sample", "_role": "sample"}


def _stub_selection(widget: RoleCastTable, rows: list) -> None:
    """Make the table report ``rows`` as selected.

    ``get_selected_rows`` round-trips to AG Grid in the browser, which the
    in-process simulation cannot do, so it is replaced with an async stub.
    """

    async def _selected_rows():
        return list(rows)

    widget.table.get_selected_rows = _selected_rows


def _grid_roles(widget: RoleCastTable) -> dict[int, tuple[str, str]]:
    return {row["ID"]: (row["Role"], row["_role"]) for row in widget.table.options["rowData"]}


def _buttons(widget: RoleCastTable) -> list:
    """The three role buttons followed by **Remove Runs**."""
    return [*widget._role_buttons.values(), widget._remove_button]


def _buttons_enabled(widget: RoleCastTable) -> list[bool]:
    return [button.enabled for button in _buttons(widget)]


async def test_role_table_renders(user: User) -> None:
    await user.open("/roles")
    await user.should_see(kind=RoleCastTable)
    await user.should_see(kind=RunTable)
    for label in (SAMPLE_BUTTON_LABEL, BACKGROUND_BUTTON_LABEL, EMPTY_CELL_BUTTON_LABEL, REMOVE_BUTTON_LABEL):
        await user.should_see(label)

    widget = _widget(user)
    assert [column["field"] for column in widget.table.options["columnDefs"]] == list(COLUMNS)
    assert widget.table.options["rowData"] == []


async def test_role_buttons_start_disabled(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)

    assert _buttons_enabled(widget) == [False] * 4
    # The buttons belong to the widget column, below the table.
    assert widget._buttons_row.parent_slot.parent is widget
    for button in _buttons(widget):
        assert button.parent_slot.parent is widget._buttons_row


async def test_role_buttons_follow_the_selection(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1)])

    _stub_selection(widget, [_grid_row(1)])
    await widget._on_selection_change()
    assert _buttons_enabled(widget) == [True] * 4

    _stub_selection(widget, [])
    await widget._on_selection_change()
    assert _buttons_enabled(widget) == [False] * 4


async def test_add_runs_shows_every_run_as_a_sample(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)

    # The table lists runs highest first, whatever order they are passed in.
    widget.add_runs([_row(1), _row(2)])

    assert widget.table.options["rowData"] == [
        {"ID": 2, "Name": "title 2", "Role": "sample", "Thickness": None, "Transmission": None, "_role": "sample"},
        {"ID": 1, "Name": "title 1", "Role": "sample", "Thickness": None, "Transmission": None, "_role": "sample"},
    ]


@pytest.mark.parametrize(
    ("role", "label"),
    [
        (MeasurementType.BACKGROUND, "background"),
        (MeasurementType.EMPTY_CELL, "empty cell"),
        (MeasurementType.SAMPLE, "sample"),
    ],
)
async def test_role_button_assigns_the_selection(user: User, role: MeasurementType, label: str) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1), _row(2), _row(3)])
    _stub_selection(widget, [_grid_row(3), _grid_row(1)])
    await widget._on_selection_change()

    await widget._on_assign(role)

    assert _grid_roles(widget) == {
        1: (label, role.value),
        2: ("sample", "sample"),
        3: (label, role.value),
    }
    await user.should_see(ASSIGNED_MESSAGE.format(n=2, role=label))
    # The redraw drops the selection, so the buttons are disabled again.
    assert _buttons_enabled(widget) == [False] * 4


def _measurement_row(run_id: int, title: str) -> dict:
    row = _row(run_id)
    row["Title"] = title
    return row


@pytest.mark.parametrize(
    ("role", "label"),
    [
        (MeasurementType.BACKGROUND, "background"),
        (MeasurementType.EMPTY_CELL, "empty cell"),
        (MeasurementType.SAMPLE, "sample"),
    ],
)
async def test_role_button_assigns_every_run_with_the_selected_name(
    user: User, role: MeasurementType, label: str
) -> None:
    await user.open("/roles")
    widget = _widget(user)
    # The runs from the manual test: one alignment run and a six-run measurement.
    cure = "Align:500 10min cure with SI"
    widget.add_runs(
        [_measurement_row(33221, "Align:0 stop rheometer")] + [_measurement_row(n, cure) for n in range(33215, 33221)]
    )
    # Start from a role other than the one assigned, so SAMPLE is tested too.
    other = MeasurementType.BACKGROUND if role is MeasurementType.SAMPLE else MeasurementType.SAMPLE
    widget.cast.assign(range(33215, 33222), other)
    _stub_selection(widget, [{"ID": 33220, "Name": cure}])

    await widget._on_assign(role)

    roles = _grid_roles(widget)
    assert roles[33221] == (ROLE_LABELS[other], other.value)
    assert {roles[n] for n in range(33215, 33221)} == {(label, role.value)}
    await user.should_see(ASSIGNED_MESSAGE.format(n=6, role=label))


async def test_role_button_click_is_wired(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1)])
    _stub_selection(widget, [_grid_row(1)])
    await widget._on_selection_change()

    user.find(BACKGROUND_BUTTON_LABEL).click()

    await user.should_see(ASSIGNED_MESSAGE.format(n=1, role="background"))
    assert _grid_roles(widget) == {1: ("background", "background")}


async def test_run_reassigned_to_sample_returns_to_sample(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1)])
    _stub_selection(widget, [_grid_row(1)])

    await widget._on_assign(MeasurementType.BACKGROUND)
    await widget._on_assign(MeasurementType.SAMPLE)

    assert _grid_roles(widget) == {1: ("sample", "sample")}


async def test_assign_without_a_selection_changes_nothing(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1)])
    widget._set_selection_buttons_enabled(True)
    _stub_selection(widget, [])

    await widget._on_assign(MeasurementType.BACKGROUND)

    assert _grid_roles(widget) == {1: ("sample", "sample")}
    assert _buttons_enabled(widget) == [False] * 4


async def test_add_runs_again_keeps_every_run_and_clears_the_status(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1), _row(2)])
    _stub_selection(widget, [_grid_row(2)])
    await widget._on_assign(MeasurementType.BACKGROUND)

    # Run 1 is not in this fetch, but a fetch only adds runs.
    widget.add_runs([_row(2), _row(3)])

    assert _grid_roles(widget) == {
        3: ("sample", "sample"),
        2: ("background", "background"),
        1: ("sample", "sample"),
    }
    assert [row["ID"] for row in widget.table.options["rowData"]] == [3, 2, 1]
    assert widget._status.visible is False


async def test_table_rebuild_disables_the_role_buttons(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget._set_selection_buttons_enabled(True)

    widget._on_table_rebuilt()

    assert _buttons_enabled(widget) == [False] * 4
    handlers = [listener.handler for listener in widget.table._event_listeners.values() if listener.type == "gridReady"]
    assert widget._on_table_rebuilt in handlers


async def test_assignment_callbacks_fire_with_independent_copies(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    first: list = []
    second: list = []
    widget.on_assignment_change(first.append)
    widget.on_assignment_change(second.append)

    widget.add_runs([_row(1)])
    _stub_selection(widget, [_grid_row(1)])
    await widget._on_assign(MeasurementType.EMPTY_CELL)

    # One notification for add_runs, one for the button.
    assert [[a.role for a in payload] for payload in first] == [
        [MeasurementType.SAMPLE],
        [MeasurementType.EMPTY_CELL],
    ]
    # A callback editing its payload changes neither the widget nor other callbacks.
    first[-1][0].role = MeasurementType.BACKGROUND
    assert second[-1][0].role is MeasurementType.EMPTY_CELL
    assert widget.assignments[0].role is MeasurementType.EMPTY_CELL


async def test_assignments_are_copies(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1)])

    widget.assignments[0].role = MeasurementType.BACKGROUND

    assert widget.assignments[0].role is MeasurementType.SAMPLE
    assert widget.cast.assignments[0].role is MeasurementType.SAMPLE


async def test_remove_button_removes_only_the_selected_runs(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    cure = "Align:500 10min cure with SI"
    widget.add_runs([_measurement_row(n, cure) for n in range(33215, 33221)])
    widget.cast.assign([33215], MeasurementType.BACKGROUND)
    _stub_selection(widget, [{"ID": 33220, "Name": cure}, {"ID": 33217, "Name": cure}])
    await widget._on_selection_change()

    await widget._on_remove()

    # The rest of the name group stays, with its role.
    assert _grid_roles(widget) == {n: ("background", "background") for n in (33219, 33218, 33216, 33215)}
    await user.should_see(REMOVED_MESSAGE.format(n=2))
    assert _buttons_enabled(widget) == [False] * 4


async def test_remove_button_click_is_wired(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1), _row(2)])
    _stub_selection(widget, [_grid_row(1)])
    await widget._on_selection_change()

    user.find(REMOVE_BUTTON_LABEL).click()

    await user.should_see(REMOVED_MESSAGE.format(n=1))
    assert list(_grid_roles(widget)) == [2]


async def test_remove_without_a_selection_removes_nothing(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1)])
    widget._set_selection_buttons_enabled(True)
    _stub_selection(widget, [])

    await widget._on_remove()

    assert list(_grid_roles(widget)) == [1]
    assert _buttons_enabled(widget) == [False] * 4


async def test_remove_notifies_the_callbacks(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1), _row(2)])
    seen: list = []
    widget.on_assignment_change(seen.append)
    _stub_selection(widget, [_grid_row(2)])

    await widget._on_remove()

    assert [[a.run_number for a in payload] for payload in seen] == [[1]]


async def test_rows_get_one_class_per_role(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    options = widget.table.options

    # Every row carries the table's own class, which scopes the role CSS.
    assert options["rowClass"] == ROW_CLASS
    # The ":" prefix makes NiceGUI compile each rule into a JS function; each rule
    # tests the hidden raw value, not the display label.
    assert options["rowClassRules"] == {
        ":usansemble-role-sample": '(params) => params.data?._role === "sample"',
        ":usansemble-role-background": '(params) => params.data?._role === "background"',
        ":usansemble-role-empty-cell": '(params) => params.data?._role === "empty_cell"',
    }
    assert set(ROLE_ROW_CLASSES) == set(MeasurementType)


async def test_row_class_rules_survive_a_redraw(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    rules = dict(widget.table.options["rowClassRules"])
    widget.add_runs([_row(1)])
    _stub_selection(widget, [_grid_row(1)])

    await widget._on_assign(MeasurementType.BACKGROUND)

    assert widget.table.options["rowClassRules"] == rules
    assert widget.table.options["rowClass"] == ROW_CLASS
    assert widget.table.options["rowData"][0]["_role"] == "background"


def test_role_css_colors_each_role() -> None:
    assert ROLE_ROW_COLORS == {
        MeasurementType.SAMPLE: "#ffffff",
        MeasurementType.BACKGROUND: "#fce4ec",
        MeasurementType.EMPTY_CELL: "#e3f2fd",
    }
    for role, css_class in ROLE_ROW_CLASSES.items():
        # !important wins over the theme's row background, including odd-row shading.
        assert (
            f".ag-row.{ROW_CLASS}.{css_class} {{ background-color: {ROLE_ROW_COLORS[role]} !important; }}" in ROLE_CSS
        )


def test_role_css_keeps_selected_rows_visible() -> None:
    # The selection layer is drawn over the role color, scoped to this table.
    rule = next(line for line in ROLE_CSS.splitlines() if "ag-row-selected" in line)
    assert rule.startswith(f".ag-row.{ROW_CLASS}.ag-row-selected::before {{")
    assert "background-color: rgba(" in rule
    assert "!important" in rule


async def test_name_column_takes_most_of_the_width(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)
    options = widget.table.options

    # NiceGUI's fit-to-width strategy overrides flex, so it must be gone.
    assert "autoSizeStrategy" not in options
    flex = {column["field"]: column["flex"] for column in options["columnDefs"]}
    assert flex == {"ID": 1, "Name": 3, "Role": 1, "Thickness": 1, "Transmission": 1}
    name = next(column for column in options["columnDefs"] if column["field"] == "Name")
    assert name["tooltipField"] == "Name"


@pytest.mark.parametrize("action", ["assign", "remove", "add_runs"])
async def test_refresh_replaces_rows_without_rebuilding_the_grid(user: User, monkeypatch, action: str) -> None:
    await user.open("/roles")
    widget = _widget(user)
    widget.add_runs([_row(1), _row(2)])
    _stub_selection(widget, [_grid_row(1)])
    updates: list = []
    grid_calls: list = []
    # update() rebuilds the grid in the browser, discarding the column widths,
    # column order and scroll position the user set.
    monkeypatch.setattr(widget.table, "update", lambda: updates.append(True))
    monkeypatch.setattr(widget.table, "run_grid_method", lambda name, *args: grid_calls.append((name, *args)))

    if action == "assign":
        await widget._on_assign(MeasurementType.BACKGROUND)
    elif action == "remove":
        await widget._on_remove()
    else:
        widget.add_runs([_row(3)])

    assert updates == []
    assert grid_calls == [("setGridOption", "rowData", widget.table.options["rowData"]), ("deselectAll",)]
    assert widget.table.options["rowData"] == widget.cast.as_rows()


async def test_rows_are_identified_by_run_number(user: User) -> None:
    await user.open("/roles")
    widget = _widget(user)

    # With row IDs, replacing the row data updates rows in place and keeps the
    # scroll position.
    assert widget.table.options[":getRowId"] == '(params) => String(params.data["ID"])'
