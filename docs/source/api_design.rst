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

Callbacks
~~~~~~~~~

Callbacks are an optional feature a client application can use to get informed
by the API when some event happens. To subscribe and unsubscribe from this
feature, send queries to the ``/callbacks`` endpoints. The old version of
callbacks used ``GET`` queries for pushing database transactions directly.
However, it turned out that was neither performant not very client-friendly.
The new approach uses a single ``POST`` endpoint on the client application, which
might optionally be protected by HTTP Bearer authentication using static tokens.
Events are be buffered up to a few seconds to improve performance even further.
Those changes were introduced in version *v0.5*. See GitHub Issue
`#101 <https://github.com/hopfenspace/MateBot/issues/101>`_ for details.

The JSON payload sent to the callback URL configured by the client application
is a list of ``Event`` objects of the following form:

.. code-block:: javascript

    {
        "number": 3,
        "events": [
            {
                "event": "NAME_OF_THE_EVENT",
                "timestamp": UNIX_TIMESTAMP,
                "data": {
                    // Any further data supplied with the event callback
                }
            },
            {
                ...
            }
        ]
    }


Currently, the following event types with their custom additional data are
implemented:

- ``server_started``

  - ``base_url`` refers to an optional commonly known base URL where the API is
    usually reachable (excluding API versions and trailing ``/``; may be ``null``
    if unspecified or unknown)

- ``alias_confirmation_requested``

  - ``id`` refers to the unconfirmed alias
  - ``user`` refers to the user ID ('owner' of the alias)
  - ``app`` refers to the application name of the alias

- ``alias_confirmed``

  - ``id`` refers to the confirmed alias
  - ``user`` refers to the user ID ('owner' of the alias)
  - ``app`` refers to the application name of the alias

- ``communism_created``

  - ``id`` refers to the created communism
  - ``user`` refers to the user ID of the creating user
  - ``amount`` refers to the total amount to be shared in the communism
  - ``participants`` is the number of participants in the communism
    (static ``1`` for this event)

- ``communism_updated``

  - ``id`` refers to the updated communism
  - ``participants`` is the new number of participants in the communism
    (accumulating multiple quantities)

- ``communism_closed`` (this event will also be fired for
  successful ``abort`` operations)

  - ``id`` refers to the closed communism
  - ``transactions`` refers to the number of transactions originating
    from closing this communism
  - ``aborted`` determines if the communism was aborted
    (``false`` for normal closing)
  - ``participants`` is the final number of participants in the communism
    (accumulating multiple quantities)

- ``poll_created``

  - ``id`` refers to the created poll
  - ``user`` refers to the user ID which has requested to become an internal user
  - ``variant`` is an enum determining the type of poll
    (i.e. whether to get or loose the internal or permission flag)

- ``poll_updated``

  - ``id`` refers to the updated poll
  - ``last_vote`` refers to the optional ID of the last vote
    (``null`` if the update wasn't triggered by a new vote)
  - ``current_result`` refers to the current balance (positive means users
    approved the request, negative means users disapproved the request)

- ``poll_closed`` (this event will also be fired for
  successful ``abort`` operations)

  - ``id`` refers to the closed poll
  - ``accepted`` determines if the poll was accepted or not
  - ``aborted`` determines if the poll was aborted (``false`` for normal closing)
  - ``variant`` is an enum determining the type of poll
    (i.e. whether to get or loose the internal or permission flag)
  - ``user`` refers to the user ID (ignoring whether the request has been accepted or not)
  - ``last_vote`` refers to the optional ID of the last vote
    (``null`` for aborted polls)

- ``refund_created``

  - ``id`` refers to the created refund
  - ``user`` refers to the user ID of the creating user
  - ``amount`` refers to the total amount the creating
    user wants from the community

- ``refund_updated``

  - ``id`` refers to the updated refund
  - ``last_vote`` refers to the optional ID of the last vote
    (``null`` for aborted refunds)
  - ``current_result`` refers to the current balance (positive means users
    approved the request, negative means users disapproved the request)

- ``refund_closed`` (this event will also be fired for
  successful ``abort`` operations)

  - ``id`` refers to the closed refund
  - ``accepted`` determines if the refund was accepted or not
  - ``aborted`` determines if the refund was aborted
    (``false`` for normal closing)
  - ``transaction`` refers to the transaction ID associated with
    the refund (``null`` for failed & aborted refunds)

- ``transaction_created``

  - ``id`` refers to the created transaction
  - ``sender`` refers to the user ID of the sender
  - ``receiver`` refers to the user ID of the receiver
  - ``amount`` refers to the amount of the transaction

- ``voucher_updated``

  - ``id`` refers to the user which has been updated, i.e. the debtor user
  - ``voucher`` refers to the optional ID of the vouching user
  - ``transaction`` refers to the optional transaction ID
    when a voucher stopped vouching for a debtor

- ``user_softly_deleted``

  - ``id`` refers to the user that has been softly deleted

- ``user_updated``

  - ``id`` refers to the user that has been updated


Example
~~~~~~~

Let's assume a new communism should be created. Then, a ``POST`` query is
sent to the ``/communisms`` endpoint. It should contain it's data as JSON
body, for example the following object:

.. code-block:: javascript

    {
      "amount": 1337,
      "description": "foo",
      "creator": 2
    }


If the client application is authenticated and everything completed without
problems, this would create a ``201`` response with the following body:

.. code-block:: javascript

    {
      "id": 1,
      "amount": 1337,
      "description": "foo",
      "creator_id": 2,
      "active": true,
      "created": 1652190970,
      "modified": 1652190970,
      "participants": [
        {
          "user_id": 2,
          "quantity": 1
        }
      ],
      "multi_transaction": null
    }


Additionally, it would a trigger a callback ``communism_created``. Since
nothing else happened on the side of the API server in the last seconds,
this would result in the following request to any configured callback server:

.. code-block:: javascript

    {
      "number": 1,
      "events": [
        {
          "event": "communism_created",
          "timestamp": 1652198170,
          "data": {
            "id": 2,
            "user": 2,
            "amount": 1337,
            "participants": 1
          }
        }
      ]
    }
