"""
MateBot core REST API definition version 1

This API provides no security model at all, at least at the moment.
It's an all-or-nothing API, so take care when deploying it. It's
recommended to put a reverse proxy in front of this API to prevent
various problems and to introduce proper authentication or user handling.

The API tries to always return JSON-encoded data to any kind of request,
if return data is necessary for that response, which is not the case for
redirects, for example. The only exception is 500 (Internal Server Error),
where no assumptions of the returned values can be made, even though even
those responses _should_ use the schema of the `APIError`, which is used
by all error responses issued by this API. This allows user agents to make
certain assumptions about the returned response, if the returned status
code equals the expected status code for that operation, usually 200 (OK).
Note that the Unprocessable Entity (422) error response means a problem in
the implementation in the user agent -- clients should never see any data
of the Unprocessable Entity responses, since the `details` field may
contain arbitrary data which is usually not user-friendly.

This API supports conditional HTTP requests and will enforce them for
various types of request that change a resource's state. Any resource
delivered or created by a request will carry the `ETag` header
set properly (exceptions are any kind of error response or those
tagged 'generic'). This allows the API to effectively prevent race
conditions when multiple clients want to update the same resource
using `PUT`. Take a look into RFC 7232 for more information. Note
that the `If-Match` header field is the only one used by this API.

The handling of incoming conditional requests is described as follows:

1. Calculate the current `ETag` of the local resource in question
2. In case the `If-Match` header field contains the special value `*` ...
    1. and the previous step returned no valid `ETag`, because the resource
       in question doesn't exist yet, respond with 412 (Precondition Failed)
    2. and the resource in question exists, perform the operation as usual
3. In case the `If-Match` header field contains that tag ...
    1. and the method is `GET`, respond with 304 (Not Modified)
    2. and for other methods, perform the operation as usual
4. Otherwise ...
    1. and the method is `GET` or `POST`, perform the operation as usual
    2. and for other methods, respond with 412 (Precondition Failed)
"""
