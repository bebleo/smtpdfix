class Authenticator():
    def __call__(self, server, session, envelope, mechanism, auth_data):
        # We don't implement the call and override this to prevent use
        raise NotImplementedError()  # pragma: no cover

    def validate(self, username, password):
        raise NotImplementedError()  # pragma: no cover

    def verify(self, username):
        raise NotImplementedError()  # pragma: no cover

    def get_password(self, username):
        raise NotImplementedError()  # pragma: no cover
