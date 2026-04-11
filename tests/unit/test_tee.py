"""Unit tests for src/utils/tee.py — Tee output utility."""

import sys


def test_tee_write_duplicates_to_stdout(capsys):
    from utils.tee import Tee

    tee = Tee()
    tee.write("hello world")

    # Should capture in StringIO buffer
    assert tee.getvalue() == "hello world"

    # Should also write to stdout
    captured = capsys.readouterr()
    assert "hello world" in captured.out


def test_tee_flush_does_not_raise():
    from utils.tee import Tee

    tee = Tee()
    tee.flush()  # Should not raise


def test_tee_multiple_writes():
    from utils.tee import Tee

    tee = Tee()
    tee.write("first")
    tee.write(" second")

    assert tee.getvalue() == "first second"


def test_tee_preserves_stdout_reference():
    from utils.tee import Tee

    tee = Tee()
    assert tee.stdout is sys.stdout
