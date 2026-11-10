class AppError(Exception):
    """An error with a code and a message that's safe to show the user."""

    status = 500
    code = "SERVER_ERROR"
    message = "Something went wrong on our side. Try again."

    def __init__(self, message=None):
        if message:
            self.message = message
        super().__init__(self.message)


class NotConfigured(AppError):
    status = 503
    code = "NOT_CONFIGURED"
    message = "Routing isn't set up on the server yet."


class UpstreamError(AppError):
    status = 502
    code = "UPSTREAM_ERROR"

    def __init__(self, service, status=None):
        self.service = service
        self.upstream_status = status
        if status == 429:
            self.status = 503
            msg = f"{service} is busy right now. Try again in a minute."
        else:
            msg = f"Couldn't get data from {service}. Try again in a minute."
        super().__init__(msg)


class NoRoute(AppError):
    status = 422
    code = "NO_ROUTE"
    message = "Couldn't find a truck route between those places. Try points closer to a road."


class ForecastUnavailable(AppError):
    status = 502
    code = "FORECAST_UNAVAILABLE"
    message = "The weather forecast doesn't cover this trip. Try an earlier departure."
