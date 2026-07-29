from simdb.cli.remote_api import select_api_version


def test_selects_highest_common_version():
    assert (
        select_api_version(["v1", "v1.1", "v1.2", "v1.3"], ("v1", "v1.1", "v1.2"))
        == "v1.2"
    )
    assert select_api_version(["v1", "v1.1"], ("v1", "v1.1", "v1.2")) == "v1.1"


def test_no_common_version_returns_none():
    assert select_api_version(["v2"], ("v1", "v1.1", "v1.2")) is None
    assert select_api_version([], ("v1", "v1.1", "v1.2")) is None


def test_versions_compare_semantically_not_lexicographically():
    assert select_api_version(["v1.2", "v1.10"], ("v1.2", "v1.10")) == "v1.10"
