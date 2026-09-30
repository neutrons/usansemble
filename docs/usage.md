# Usage

Launch the app with Pixi:

```bash
pixi run start
```

This starts the NiceGUI server on <http://127.0.0.1:8080>. The console script
`usansemble` (installed with the package) and `python -m usansemble.main` are
equivalent entry points. Useful flags:

- `--host` / `--port` — interface and port to bind (default `127.0.0.1:8080`).
- `--storage-secret` — secret used to sign the per-browser cookie that persists
  your ONCat token. A development default is used when omitted; set your own for
  any real deployment.
- `--native` — open in a native desktop window instead of a browser tab.

## The RunsSelector widget

The landing page mounts a `RunsSelector`, a composite widget that packages
pyoncatng's `OncatLogin` and `IPTSTable`:

1. Click **Connect** and approve the ONCat sign-in in your browser.
2. Type an IPTS number (e.g. `24703`) and click **Load** to fetch that
   experiment's USANS runs.
3. Select runs in the table: click selects one run, Ctrl/Cmd+click toggles a run,
   Shift+click selects a range, and double-click selects every run with the same
   title. Ctrl/Cmd+double-click adds that title group to the selection.
4. Click **Clear Selection** to deselect all highlighted runs and start over.
   Like **Fetch Runs**, this button is enabled only while the table has a
   selection. Clearing the selection disables both buttons again.
5. Click **Fetch Runs** to capture the highlighted runs. The button stays
   disabled until the table has a selection, and the captured runs are ordered
   by decreasing run number, as the table lists them, regardless of the order
   they were selected in.
   Loading another IPTS clears the selection and disables the button again;
   the runs fetched before it are kept. Each click replaces the previous
   capture, so the widget holds exactly the runs highlighted at the last click.
   The role table below adds each capture to the runs it already holds; see
   the next section.

## The RoleCastTable widget

Below the `RunsSelector`, the landing page mounts a `RoleCastTable`, where each
fetched run is assigned the role it plays in the reduction: sample, background
or empty cell. The table lists each run's ID, Name (its title), Role, Thickness
and Transmission, by decreasing run number. Thickness and Transmission are
empty for now.

1. Click **Fetch Runs** in the `RunsSelector` to add the highlighted runs to the
   role table. Each fetch adds runs; runs already in the table stay, with their
   role. A new run starts as a sample, unless runs with the same Name are
   already in the table, in which case it takes their role.
2. Select runs in the role table: click selects one run, Ctrl/Cmd+click toggles
   a run, and Shift+click selects a range.
3. Click **Set as Background**, **Set as Empty Cell** or **Set as Sample** to
   assign that role. The runs of one measurement share a Name, so a button
   assigns the role to every run with the same Name as a selected run. Runs
   with the same Name therefore always have the same role. Names are compared
   exactly, including case and spaces.
4. Click **Remove Runs** to take the selected runs out of the table. Only the
   selected runs are removed; other runs with the same Name stay, with their
   role.

The four buttons are enabled only while the role table has a selection. After
each click the selection is cleared, and a status line below the buttons
reports how many runs were assigned or removed.

Each row is colored by its role: white for sample, light pink for background
and light blue for empty cell.

Exporting the `usansred` JSON configuration is planned for a subsequent
iteration.
