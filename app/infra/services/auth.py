import secrets

from app.application.interfaces.services import AuthenticatorServiceInterface


class SafetyAuthenticatorService(AuthenticatorServiceInterface):
    def __init__(self, excpected: str):
        self.__excpected = excpected

    def authenticate(self, key: str) -> bool:
        return secrets.compare_digest(key, self.__excpected)
