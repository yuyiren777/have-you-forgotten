from pathlib import Path

import db.database as database
from core.reminder import LOCAL_TIMEZONE, scheduler


def test_packaged_data_uses_local_app_data(monkeypatch, tmp_path):
    monkeypatch.setattr(database.sys, "frozen", True, raising=False)
    monkeypatch.setenv("LOCALAPPDATA", str(tmp_path))
    assert database._get_data_dir() == str(tmp_path / "HaveYouForgotten")


def test_scheduler_has_an_explicit_local_timezone():
    assert scheduler.timezone == LOCAL_TIMEZONE


def test_installer_cleans_processes_autostart_and_app_data():
    script = (Path(__file__).parents[1] / "installer" / "AI-Memo.iss").read_text(
        encoding="utf-8"
    )
    assert "DisableDirPage=no" in script
    assert "UsePreviousAppDir=yes" in script
    assert "CloseApplicationsFilter={#MyAppExeName}" in script
    assert "taskkill.exe" in script
    assert "RegDeleteValue(HKEY_CURRENT_USER" in script
    assert 'Name: "{localappdata}\\HaveYouForgotten"' in script


def test_installer_distinguishes_updates_from_first_install():
    script = (Path(__file__).parents[1] / "installer" / "AI-Memo.iss").read_text(
        encoding="utf-8"
    )

    assert "function PreviousInstallationExists" in script
    assert "RegKeyExists(HKEY_CURRENT_USER" in script
    assert "RegKeyExists(HKEY_LOCAL_MACHINE" in script
    assert "function ShouldSkipPage(PageID: Integer): Boolean" in script
    assert "wpSelectDir" in script
    assert "wpReady" in script
    assert "WizardForm.NextButton.Caption := '更新'" in script
    assert "现有日程、设置和提醒记录会保留" in script
