.. _code_conventions:

================
Code Conventions
================

.. toctree::

General information
-------------------

We always try to stick to the rules of
`PEP8 <https://www.python.org/dev/peps/pep-0008/>`_
as close as possible. The indentation for Python files
is considered to be 4 spaces. The same applies to
reStructuredText files. The JSON file ``config.json``
(see :ref:`config`) uses tabs for indentation, but the
indentation is optional in this case anyway.

Python files
------------

  * Any Python module should have a module docstring.
    The docstrings should line out important aspects of a
    function, method, class or module. We discourage
    undocumented features, even if they are considered "private".
  * We try to give the functions and classes names that
    explain themselves. Functions and methods are named
    snake_case style, classes PascalCase style. Usually,
    modules should not contain more than one word, anyway.
  * Python source code files should not be very long. More
    than 100 characters in one line are discouraged, see
    `PEP8 <https://www.python.org/dev/peps/pep-0008/#id19>`_.
  * We try to use type annotations where possible. See
    `PEP484 <https://www.python.org/dev/peps/pep-0484/>`_
    for more information about it. If type annotations are not
    possible, e.g. due to necessary imports, the type hints
    should be outlined in the docstrings for the feature.
  * Docstrings in the whole project use the extended features
    for reStructuredText in combination with the Python documentation
    framework `Sphinx <https://www.sphinx-doc.org/>`_.
