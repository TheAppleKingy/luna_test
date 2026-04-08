from typing import Protocol


class AuthenticatorServiceInterface(Protocol):
    def authenticate(self, key: str) -> bool: ...
