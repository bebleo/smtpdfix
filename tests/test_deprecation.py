import pytest

from smtpdfix.certs import generate_certs


def test_deprecate_gen_certs(tmp_path_factory):
    path = tmp_path_factory.mktemp("tmp")
    with pytest.warns(PendingDeprecationWarning):
        generate_certs(path)
