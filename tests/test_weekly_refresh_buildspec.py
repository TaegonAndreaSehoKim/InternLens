from pathlib import Path


def test_weekly_refresh_buildspec_refreshes_packages_and_deploys() -> None:
    buildspec = Path("buildspec.weekly-refresh.yml").read_text(encoding="utf-8")

    assert "python scripts/refresh_job_corpus.py" in buildspec
    assert "python -m pytest -q" in buildspec
    assert "python scripts/package_eb.py --output-file outputs/internlens_eb_backend.zip" in buildspec
    assert "aws s3 cp outputs/internlens_eb_backend.zip" in buildspec
    assert "aws elasticbeanstalk create-application-version" in buildspec
    assert "aws elasticbeanstalk update-environment" in buildspec
    assert "aws elasticbeanstalk wait environment-updated" in buildspec
    assert 'test "${DEPLOYED_VERSION}" = "${VERSION_LABEL}"' in buildspec


def test_weekly_refresh_buildspec_requires_explicit_aws_targets() -> None:
    buildspec = Path("buildspec.weekly-refresh.yml").read_text(encoding="utf-8")

    assert "EB_APPLICATION_NAME:?" in buildspec
    assert "EB_ENVIRONMENT_NAME:?" in buildspec
    assert "EB_ARTIFACT_BUCKET:?" in buildspec
