Build & Publish
===============

Conda packages
--------------

Conda packages are supported; all build and publishing steps are defined as
Pixi tasks:

.. code-block:: bash

   pixi run conda-build
   pixi run conda-publish

Conda packages are published to the `anaconda.org/neutrons <https://anaconda.org/neutrons>`_
organization.

Documentation
-------------

Build the documentation with:

.. code-block:: bash

   pixi run build-docs
