import pytest
from app.security import safe_relative_path, should_exclude

def test_safe_path():
    assert safe_relative_path("src/main.py") == "src/main.py"

@pytest.mark.parametrize("path", ["../secret", "/absolute", ".env", "node_modules/a.js", "a\\b.py"])
def test_reject_unsafe_path(path):
    with pytest.raises(ValueError):
        safe_relative_path(path)

def test_exclusions():
    assert should_exclude(".env")
    assert should_exclude("node_modules/pkg/a.js")
    assert not should_exclude("src/app.py")
