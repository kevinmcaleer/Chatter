"""return_to may send people back to another kevsrobots.com app after signing in, and nowhere else."""
from app.auth import is_kevsrobots_url, sanitize_return_to


def test_relative_paths_still_work():
    assert sanitize_return_to("/account") == "/account"
    assert sanitize_return_to("projects") == "/projects"
    assert sanitize_return_to("/login?x=1") is None


def test_kevsrobots_sites_are_allowed():
    url = "https://bettercad.kevsrobots.com/#/library"
    assert sanitize_return_to(url) == url
    assert sanitize_return_to("https://kevsrobots.com/learn/") == "https://kevsrobots.com/learn/"


def test_other_absolute_urls_are_refused():
    for url in [
        "https://evil.com/",
        "https://kevsrobots.com.evil.com/",
        "https://evilkevsrobots.com/",
        "http://bettercad.kevsrobots.com/",
        "https://user@bettercad.kevsrobots.com/",
        "https://bettercad.kevsrobots.com:8443/",
        "https://bettercad.kevsrobots.com\\@evil.com/",
        "//bettercad.kevsrobots.com/",
        "https://www.kevsrobots.com/login?return_to=x",
        "https://chatter.kevsrobots.com/register",
        "https://bettercad.kevsrobots.com/" + "x" * 600,
    ]:
        assert sanitize_return_to(url) is None, url
    assert not is_kevsrobots_url("https://[bad/")
