# test_env.py
import os
from pathlib import Path

from tonofdevelopervoice.env import load_dotenv


def test_load_dotenv_sets_new_vars_and_skips_comments(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("# comment\nFOO_TEST_VAR=bar\n\nBAZ_TEST_VAR=qux\n")
    os.environ.pop("FOO_TEST_VAR", None)
    os.environ.pop("BAZ_TEST_VAR", None)
    try:
        load_dotenv(env_file)
        assert os.environ["FOO_TEST_VAR"] == "bar"
        assert os.environ["BAZ_TEST_VAR"] == "qux"
    finally:
        os.environ.pop("FOO_TEST_VAR", None)
        os.environ.pop("BAZ_TEST_VAR", None)


def test_load_dotenv_does_not_override_existing_env(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text("EXISTING_TEST_VAR=fromfile\n")
    os.environ["EXISTING_TEST_VAR"] = "fromenv"
    try:
        load_dotenv(env_file)
        assert os.environ["EXISTING_TEST_VAR"] == "fromenv"
    finally:
        os.environ.pop("EXISTING_TEST_VAR", None)


def test_load_dotenv_missing_file_is_a_noop(tmp_path: Path) -> None:
    load_dotenv(tmp_path / "does-not-exist.env")


def test_load_dotenv_strips_surrounding_quotes(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text('DQUOTE_TEST_VAR="abc123"\nSQUOTE_TEST_VAR=\'xyz789\'\n')
    os.environ.pop("DQUOTE_TEST_VAR", None)
    os.environ.pop("SQUOTE_TEST_VAR", None)
    try:
        load_dotenv(env_file)
        assert os.environ["DQUOTE_TEST_VAR"] == "abc123"
        assert os.environ["SQUOTE_TEST_VAR"] == "xyz789"
    finally:
        os.environ.pop("DQUOTE_TEST_VAR", None)
        os.environ.pop("SQUOTE_TEST_VAR", None)
