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
   by increasing run number regardless of the order they were selected in.
   Loading another IPTS clears the selection and disables the button again;
   the runs fetched before it are kept. Each click replaces the previous
   capture, so the widget holds exactly the runs highlighted at the last click.

Assigning runs to roles (sample / background / empty cell / empty beam) and
exporting the `usansred` JSON configuration are planned for subsequent
iterations.
