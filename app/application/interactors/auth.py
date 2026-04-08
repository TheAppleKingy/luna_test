from typing import Optional

from app.application.interfaces.services import AuthenticatorServiceInterface
from app.application.err import NoCredentialsError


class Authenticate:
    def __init__(self, authenticator: AuthenticatorServiceInterface):
        self._authenticator = authenticator

    def __call__(self, key: Optional[str]) -> bool:
        if not key:
            raise NoCredentialsError("Api key was not provide", status=401)
        return self._authenticator.authenticate(key)
