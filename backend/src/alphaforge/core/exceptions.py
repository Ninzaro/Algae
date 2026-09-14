class AlphaForgeError(Exception):
    """Base error for all AlphaForge exceptions."""

    def __init__(self, message: str, *, code: str = "internal_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class ConfigurationError(AlphaForgeError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="configuration_error")


class ValidationError(AlphaForgeError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="validation_error")


class NotFoundError(AlphaForgeError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="not_found")


class AuthenticationError(AlphaForgeError):
    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, code="unauthenticated")


class AuthorizationError(AlphaForgeError):
    def __init__(self, message: str = "Not authorized") -> None:
        super().__init__(message, code="forbidden")


class RiskRejectedError(AlphaForgeError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="risk_rejected")


class KillSwitchActiveError(RiskRejectedError):
    def __init__(self, message: str = "Kill switch is active") -> None:
        super().__init__(message)
        self.code = "kill_switch_active"


class BrokerError(AlphaForgeError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="broker_error")


class DataError(AlphaForgeError):
    def __init__(self, message: str) -> None:
        super().__init__(message, code="data_error")
