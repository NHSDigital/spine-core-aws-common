from spine_aws_common.log.log_helper import LogHelper, sys


def test_log_helper_capture():
    log_helper = LogHelper()
    log_helper.set_stdout_capture()
    sys.stdout.write("hello\n")
    sys.stdout.write("\n\n\n")
    sys.stdout.write("world")
    sys.stdout.flush()

    assert list(log_helper.log_lines()) == ["hello", "world"]


def test_log_helper_capture_log_reference_filter():
    log_helper = LogHelper()
    log_helper.set_stdout_capture()
    sys.stdout.write("logReference=BCD123 - log1\n")
    sys.stdout.write("logReference=ABC123a - log1\n")

    assert log_helper.was_logged(log_reference="ABC123a")
    assert log_helper.was_logged(log_reference="BCD123")
    assert not log_helper.was_logged(log_reference="ABC123")


def test_log_helper_capture_log_reference_entries_filter():
    log_helper = LogHelper()
    log_helper.set_stdout_capture()
    sys.stdout.write("logReference=BCD123 - log1 abc=123 def=\"aa\" ged='oo'\n")
    sys.stdout.write("logReference=ABC123a - log1\n")

    assert log_helper.was_logged(log_reference="BCD123")
    entry = next(log_helper.find_log_entries(log_reference="BCD123"))
    assert entry
    assert entry == {"logReference": "BCD123", "abc": "123", "def": "aa", "ged": "oo"}
