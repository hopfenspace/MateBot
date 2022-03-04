"""
MateBot error schemas
"""

from typing import Optional

import pydantic


class APIError(pydantic.BaseModel):
    """
    APIError: shared model for all types of API failures

    Whenever some kind of problem occurs during request handling and some
    exception handler took over, the answer will be some kind of this model.
    The only exception is `500` (Internal Server Error), since they might
    not get caught anymore. Fields of this model can be used for client-side
    error handling and might even be shown to end users in an adequate form.

    The field `error` should always contain a true boolean value for
    backward compatibility. The field `status` contains the HTTP status code
    of the response, if possible. The field `request` contains the request
    path without query parameters or fragments, while the `method` field
    holds the request method (e.g. `GET`). The field `repeat` determines
    whether executing the exact same request again may be successful instead.
    The field `message` contains a short human-readable informational message
    about the problem, but may not be totally adequate or user-friendly. The
    field `details` contains a string of arbitrary length with details about
    the problem source, if available, and should primarily be used for debugging.
    """

    error: bool = True
    status: Optional[pydantic.NonNegativeInt]
    method: pydantic.constr(max_length=255)
    request: str
    repeat: bool
    message: str
    details: str
