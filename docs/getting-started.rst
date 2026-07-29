Getting Started
===============

This project is managed entirely with `Pixi <https://pixi.sh/>`_, a reproducible
and declarative environment manager. All build and packaging metadata lives in a
single ``pyproject.toml``.

1. Install Pixi
---------------

.. code-block:: bash

   curl -fsSL https://pixi.sh/install.sh | bash

2. Set up the environment
-------------------------

.. code-block:: bash

   pixi install

3. Explore available tasks
---------------------------

.. code-block:: bash

   pixi run

4. Development workflow
-----------------------

.. code-block:: bash

   pixi shell            # activate the environment
   pixi run start        # launch the web app
   pixi run test         # run the test suite
   ruff check .          # lint
   pip install --no-deps -e .   # editable install

Optional direnv integration
----------------------------

If a checkout has a local ``.envrc``, developers using
`direnv <https://direnv.net/>`_ can have the Pixi environment activated
automatically when entering the repository. A typical ``.envrc`` watches
``pixi.lock`` and evaluates Pixi's shell hook:

.. code-block:: bash

   watch_file pixi.lock
   eval "$(pixi shell-hook --frozen --change-ps1 false)"

This is only a local convenience. ``.envrc`` is ignored by Git, is not required
for normal development, and may differ between developers. Without ``direnv``,
use ``pixi shell`` or ``pixi run ...`` directly.
