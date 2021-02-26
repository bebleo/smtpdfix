class Authenticator():
    def __call__(self, server, session, envelope, mechanism, auth_data):
        # We don't implement the call and override this to prevent use
        raise NotImplementedError()  # pragma: no cover

    def validate(self, username, password):
        """Validate that the passward authenticates the username."""
        raise NotImplementedError()  # pragma: no cover

    def verify(self, username):
        """Method to verify that an address or username is correct.

        Possible inputs are:
        - a user name (e.g. "user")
        - an email address (e.g. "user@example.org")

        Should return a string in the form of "User <user@example.org>" if
        the address provided is valid. If there the valid is invalid return
        None. In this case we are returning a boolean true instead.
        """
        raise NotImplementedError()  # pragma: no cover

    def get_password(self, username):
        """Returns the password for a given username."""
        raise NotImplementedError()  # pragma: no cover
