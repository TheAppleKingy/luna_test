from app.domain.err import HandlingError


class ApplicationError(HandlingError):
    pass


class NoCredentialsError(ApplicationError):
    pass


class UndefinedPaymentError(ApplicationError):
    pass
