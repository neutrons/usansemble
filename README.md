# usansemble

A [NiceGUI](https://nicegui.io/) web app to assemble the JSON reduction
configuration consumed by [usansred](https://github.com/neutrons/usansred/). It
reuses the ONCat login and run-browsing widgets from
[pyoncatng](https://github.com/neutrons/pyoncatng/) to let you sign in, browse a
USANS experiment's runs, and (soon) assign runs to roles and export a `usansred`
setup file.
[![Documentation Status](https://app.readthedocs.org/projects/usansemble/badge/?version=latest)](https://usansemble.readthedocs.io/en/latest/?badge=latest)

- **Documentation:** https://usansemble.readthedocs.io/
- **Source code:** https://github.com/neutrons/usansemble/

## Quick start

```bash
pixi install       # set up the environment
pixi run start     # launch the web app (http://127.0.0.1:8080)
pixi run test      # run the test suite
```
