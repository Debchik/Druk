import pytest
from pydantic import ValidationError
from app.schemas import SettingsPatch, GithubRepoCreate


def test_telegram_link_restricted_to_t_me():
    assert str(SettingsPatch(telegram_url='https://t.me/druk').telegram_url).startswith('https://t.me/')
    with pytest.raises(ValidationError):
        SettingsPatch(telegram_url='https://example.com/druk')


def test_github_repo_name_validation():
    assert GithubRepoCreate(full_name='owner/repo').full_name == 'owner/repo'
    with pytest.raises(ValidationError):
        GithubRepoCreate(full_name='https://github.com/owner/repo')
