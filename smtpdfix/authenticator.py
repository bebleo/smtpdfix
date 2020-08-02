class Authenticator():
    def validate(self, username, password):
        raise NotImplementedError()  # pragma: no cover

    def verify(self, username):
        raise NotImplementedError()  # pragma: no cover

    def get_password(self, username):
        raise NotImplementedError()  # pragma: no cover
