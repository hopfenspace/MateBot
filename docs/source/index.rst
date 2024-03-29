==============================================
Welcome to the MateBot core API documentation!
==============================================

.. image:: _static/matebot.png
  :width: 160
  :alt: MateBot core API logo

The API provided in this project allows clients to handle a diverse user base,
where every user has any number of associated aliases but one shared balance.
It can be sent to other users, shared in bills or refunded by the community
by a community poll, where every user has the equal privileges and voting
weight. Additionally, the API provides endpoints to easily consume any
amount of consumables and vouch for other users in case of high debts.

Most important libraries used in this project:

  * `FastAPI <https://fastapi.tiangolo.com>`_ as the web framework at the heart
  * `Pydantic <https://pydantic-docs.helpmanual.io>`_ for easy
    schema creation and validation with OpenAPI support
  * `SQLAlchemy <https://sqlalchemy.org>`_
    with `Alembic <https://alembic.sqlalchemy.org>`_
    as SQL database ORM and migration tool
  * `uvicorn <https://www.uvicorn.org>`_ as web server implementation

Table of contents
-----------------

.. toctree::
    :maxdepth: 2

    installation
    configuration
    api_design
    clients
    database
    testing
    code_conventions
    license
