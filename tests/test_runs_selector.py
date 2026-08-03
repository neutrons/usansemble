"""Tests for the RunsSelector composite widget.

``RunsSelector`` packages pyoncatng's ``OncatLogin`` + ``IPTSTable``. The tests
use NiceGUI's in-process ``user`` simulation; the ``fake_agent`` fixture patches
``pyoncatng.core.service.build_agent`` so the login card (and the table it feeds)
run against a scriptable agent. A test reaches the live element through
``user.find`` and scripts ``Run.list`` before loading.
"""

import json

import pytest
from nicegui.testing import User
from pyoncatng.widgets.iptstable import IPTSTable
from pyoncatng.widgets.login import OncatLogin

from usansemble.widgets.runs_selector import PROCESSING_VARIABLES, SELECTION_HELP, TITLE_COLUMN, RunsSelector

# A sample run as returned by ONCat with a flat, dot-path projection. USANS runs
# expose metadata under datafiles.raw.metadata.entry.*.
SAMPLE_RUN = {
    "id": 33221,
    "datafiles.raw.metadata.entry.title": "Align:0 stop rheometer",
    "datafiles.raw.metadata.entry.start_time": "2020-11-24T06:33:53.879457667-05:00",
    "datafiles.raw.metadata.entry.total_counts": 258881,
}


def _selector(user: User) -> RunsSelector:
    return next(iter(user.find(RunsSelector).elements))


async def test_runs_selector_renders(user: User, fake_agent) -> None:
    fake_agent.tokened = False
    await user.open("/runs")
    await user.should_see(kind=RunsSelector)
    await user.should_see(kind=OncatLogin)
    await user.should_see(kind=IPTSTable)
    await user.should_see("IPTS:")
    await user.should_see("Load")
    await user.should_see("Connect")


async def test_runs_selector_exposes_login_and_table(user: User, fake_agent) -> None:
    await user.open("/runs")
    selector = _selector(user)
    assert isinstance(selector.login, OncatLogin)
    assert isinstance(selector.table, IPTSTable)
    # The table shares the login's agent; both are the injected fake.
    assert selector.agent is selector.login.agent
    assert selector.table._agent is fake_agent
    assert selector.table._processing_variables == list(PROCESSING_VARIABLES)


async def test_runs_selector_load_populates_table(user: User, fake_agent) -> None:
    await user.open("/runs")
    selector = _selector(user)
    table = selector.table
    fake_agent.run_result = [SAMPLE_RUN]
    table._input.value = "24703"

    await table._on_load()

    # The IPTS number was normalized and the fixed facility/instrument were sent.
    assert fake_agent.run_kwargs["experiment"] == "IPTS-24703"
    assert fake_agent.run_kwargs["facility"] == "SNS"
    assert fake_agent.run_kwargs["instrument"] == "USANS"
    # The child RunTable carries the mapped row.
    assert table._table.options["rowData"] == [
        {
            "ID": 33221,
            "Title": "Align:0 stop rheometer",
            "Start Time": "2020-11-24T06:33:53.879457667-05:00",
            "Total Counts": 258881,
        }
    ]


@pytest.mark.usefixtures("fake_agent")
async def test_runs_selector_installs_title_double_click_handler(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)

    # The handler is a client-side AG Grid option (NiceGUI compiles a ":"-prefixed
    # key into a JS function), so only its presence and shape can be checked here.
    handler = selector.table._table.options[":onCellDoubleClicked"]
    assert "onCellDoubleClicked" not in selector.table._table.options
    # Ctrl (and Cmd on macOS) switches from replacing to appending to the selection.
    assert "ctrlKey" in handler
    assert "metaKey" in handler
    # Invalid cell events must leave the existing selection unchanged.
    assert "if (wanted == null) return;" in handler
    # Replacing clears first; both branches end by selecting the matching rows.
    assert "deselectAll" in handler
    assert "setNodesSelected" in handler


@pytest.mark.usefixtures("fake_agent")
async def test_title_double_click_handler_targets_the_title_column(user: User) -> None:
    await user.open("/runs")
    selector = _selector(user)

    # Guards against a PROCESSING_VARIABLES reorder silently pointing the gesture
    # at the wrong column.
    assert TITLE_COLUMN == "Title"
    assert json.dumps(TITLE_COLUMN) in selector.table._table.options[":onCellDoubleClicked"]


@pytest.mark.usefixtures("fake_agent")
async def test_runs_selector_shows_selection_help(user: User) -> None:
    await user.open("/runs")
    await user.should_see(SELECTION_HELP)

    # The caption belongs to the table card, so it stays with the table if the
    # surrounding layout changes.
    selector = _selector(user)
    assert selector._selection_help.parent_slot.parent is selector.table


async def test_runs_selector_on_connection_change_is_forwarded(user: User, fake_agent) -> None:
    fake_agent.tokened = False
    await user.open("/runs")
    selector = _selector(user)
    seen: list[bool] = []
    selector.on_connection_change(seen.append)

    # Firing the login's state notification reaches callbacks registered on the
    # composite widget (the pass-through contract).
    selector.login._update_connection_status()

    assert seen == [selector.login.is_connected]
