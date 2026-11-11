STATUS_CODES = {
    400: "invalid",
    401: "unauthorized",
    403: "forbidden",
    404: "not-found",
    409: "conflict",
    413: "too-large",
    415: "unsupported",
    422: "unprocessable",
    500: "internal",
}


def default_code(status: int) -> str:
    """Return the code an error answer carries when no specific one is given, chosen by its HTTP status."""
    found = STATUS_CODES.get(status)
    if found:
        return found
    if status == 421 or status == 405:
        return "invalid"
    if status == 502:
        return "upstream"
    if status == 503:
        return "unavailable"
    if status == 504:
        return "timeout"
    return "invalid" if status < 500 else "internal"
