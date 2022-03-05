.. _api_design:

==========
API Design
==========

.. toctree::

Overview
--------

The API is built with a simple versioning scheme to differentiate
between (possibly) newer endpoints in the future. Currently, only
``/v1`` endpoints are available, since the API is in its first
released iteration.

Almost all endpoints either accept query parameters or JSON-data
in the body as input (the only exception is ``/v1/login``, see
:ref:`below <api_design_v1_authentication>`).
The response from all endpoints should be JSON.

.. only:: builder_html

   Download the full :download:`OpenAPI specification <_static/openapi.json>`.

API version 1
-------------

.. _api_design_v1_authentication:

Authentication
~~~~~~~~~~~~~~

The API requires authentication using JSON web tokens. Logging in with username
and password (see ``POST /v1/login``) yields a token that should be included
in the ``Authorization`` header with the type ``Bearer``. It's an all-or-nothing
API without restrictions on queries, provided the request is valid and the
HTTP authorization with the bearer token was successful as well.

Endpoints
~~~~~~~~~

All endpoints described below must be prefixed with ``/v1``. For more
information about those endpoints, take a look into the OpenAPI specification.

============ ========== =============================== ==================================
Topic        Method     Endpoint                        Description
============ ========== =============================== ==================================
Auth         ``POST``   ``/login``                      Login
Generic      ``GET``    ``/settings``                   Get Settings
Generic      ``GET``    ``/status``                     Get Status
Searches     ``GET``    ``/applications``               Search For Applications
Searches     ``GET``    ``/ballot``                     Search For Ballots
Searches     ``GET``    ``/consumables``                Search For Consumables
Searches     ``GET``    ``/multitransactions``          Search For Multi Transactions
Searches     ``GET``    ``/votes``                      Search For Votes
Aliases      ``GET``    ``/aliases``                    Search For Aliases
Aliases      ``PUT``    ``/aliases``                    Update Existing Alias
Aliases      ``POST``   ``/aliases``                    Create New Alias
Aliases      ``DELETE`` ``/aliases``                    Delete Existing Alias
Callbacks    ``GET``    ``/callbacks``                  Search For Callbacks
Callbacks    ``PUT``    ``/callbacks``                  Update Existing Callback
Callbacks    ``POST``   ``/callbacks``                  Create New Callback
Callbacks    ``DELETE`` ``/callbacks``                  Delete Existing Callback
Communisms   ``GET``    ``/communisms``                 Search For Communisms
Communisms   ``POST``   ``/communisms``                 Create New Communism
Communisms   ``POST``   ``/communisms/abort``           Abort Open Communism
Communisms   ``POST``   ``/communisms/close``           Close Open Communism
Communisms   ``POST``   ``/communisms/setParticipants`` Set Participants Of Open Communism
Polls        ``GET``    ``/polls``                      Search For Polls
Polls        ``POST``   ``/polls``                      Create New Membership Poll
Polls        ``POST``   ``/polls/vote``                 Vote For Membership Request
Polls        ``POST``   ``/polls/abort``                Abort Open Membership Poll
Refunds      ``GET``    ``/refunds``                    Search For Refunds
Refunds      ``POST``   ``/refunds``                    Create New Refund
Refunds      ``POST``   ``/refunds/vote``               Vote For Refund Request
Refunds      ``POST``   ``/refunds/abort``              Abort Open Refund Request
Transactions ``POST``   ``/transactions``               Search For Transactions
Transactions ``GET``    ``/transactions``               Make A New Transaction
Users        ``GET``    ``/users``                      Search For Users
Users        ``POST``    ``/users``                     Create New User
Users        ``POST``    ``/users/setFlags``            Set Flags Of User
Users        ``POST``    ``/users/setName``             Set Name Of User
Users        ``POST``    ``/users/setVoucher``          Set Voucher Of User
Users        ``POST``    ``/users/disable``             Disable User Permanently
============ ========== =============================== ==================================
