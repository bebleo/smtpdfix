from abc import ABCMeta, abstractmethod


class Authenticator(metaclass=ABCMeta):
    @abstractmethod
    def validate(self, username: str, password: str) -> bool:
        """Validate that the passward authenticates the username."""
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def verify(self, username: str) -> bool:
        """Method to verify that an address or username is correct.

        Possible inputs are:
        - a user name (e.g. "user")
        - an email address (e.g. "user@example.org")

        Should return a string in the form of "User <user@example.org>" if
        the address provided is valid. If there the valid is invalid return
        None. In this case we are returning a boolean true instead.
        """
        raise NotImplementedError()  # pragma: no cover

    @abstractmethod
    def get_password(self, username: str) -> str:
        """Returns the password for a given username."""
        raise NotImplementedError()  # pragma: no cover
