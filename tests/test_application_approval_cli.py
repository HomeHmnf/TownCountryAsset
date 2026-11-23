from __future__ import annotations

import sys

import pytest

import tools.import_wp1_5 as wp15
import tools.import_country_data as country
import tools.database.review_data_import as review


ARTIFACT = {"artifact_sha256": "a" * 64}


class FakeConnection:
    def close(self):
        pass


def patch_approval_setup(monkeypatch, module):
    calls = []
    monkeypatch.setattr(module, "connect_database", lambda *_args, **_kwargs: FakeConnection())
    monkeypatch.setattr(module, "apply_migrations", lambda _connection: None)
    monkeypatch.setattr(
        module, "approve_application",
        lambda connection, **kwargs: calls.append(kwargs),
    )
    return calls


def test_wp15_prints_approval_id_before_failed_apply(monkeypatch, capsys):
    calls = patch_approval_setup(monkeypatch, wp15)
    monkeypatch.setattr(wp15, "validate_wp1_5_dataset", lambda **_kwargs: {
        "application_artifact": ARTIFACT,
    })
    monkeypatch.setattr(
        wp15, "import_wp1_5_dataset",
        lambda **_kwargs: (_ for _ in ()).throw(wp15.StatisticsImportError("simulated apply failure")),
    )
    monkeypatch.setattr(sys, "argv", [
        "import_wp1_5", "--observations", "obs.json", "--crosswalk", "crosswalk.json",
        "--manifest", "manifest.json", "--database", "db.sqlite",
        "--approve-and-apply", "--actor", "reviewer", "--note", "Reviewed inputs",
    ])

    assert wp15.main() == 1
    assert calls[0]["approval_id"] == "wp1-5-" + "a" * 20
    assert calls[0]["actor"] == "reviewer"
    assert calls[0]["note"] == "Reviewed inputs"
    assert "Approval created for validated inputs: wp1-5-" + "a" * 20 in capsys.readouterr().out


def test_country_data_prints_approval_id_before_failed_apply(monkeypatch, capsys):
    calls = patch_approval_setup(monkeypatch, country)
    monkeypatch.setattr(country, "build_country_data_application_artifact", lambda *_args: ARTIFACT)
    monkeypatch.setattr(
        country, "import_country_data",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(country.CountryDataImportError("simulated apply failure")),
    )
    monkeypatch.setattr(sys, "argv", [
        "import_country_data", "--candidate-dir", "candidate", "--database", "db.sqlite",
        "--approve-and-apply", "--actor", "reviewer", "--note", "Reviewed inputs",
    ])

    assert country.main() == 1
    assert calls[0]["approval_id"] == "country-data-" + "a" * 20
    assert "Approval created for validated inputs: country-data-" + "a" * 20 in capsys.readouterr().out


def test_review_data_prints_approval_id_before_failed_apply(monkeypatch, capsys):
    calls = patch_approval_setup(monkeypatch, review)
    monkeypatch.setattr(review, "build_review_application_artifact", lambda *_args: ARTIFACT)
    monkeypatch.setattr(
        review, "import_review_data",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(review.ReviewDataImportError("simulated apply failure")),
    )
    monkeypatch.setattr(sys, "argv", [
        "import_review_data", "--database", "db.sqlite", "--iso-reference", "iso.csv",
        "--iso-provenance", "iso.json", "--iso-proposals", "iso.md",
        "--persian-candidates", "fa.json", "--persian-provenance", "fa-provenance.json",
        "--approve-and-apply", "--actor", "reviewer", "--note", "Reviewed inputs",
    ])

    with pytest.raises(SystemExit) as exc:
        review.main()
    assert exc.value.code == 2
    assert calls[0]["approval_id"] == "review-data-" + "a" * 20
    assert "Approval created for validated inputs: review-data-" + "a" * 20 in capsys.readouterr().out


@pytest.mark.parametrize(
    ("module", "argv", "import_name", "expected"),
    [
        (
            wp15,
            ["import_wp1_5", "--observations", "obs.json", "--crosswalk", "cw.json",
             "--manifest", "manifest.json", "--database", "db.sqlite",
             "--approval-id", "resume-wp15-001"],
            "import_wp1_5_dataset", {"integrity": "ok"},
        ),
        (
            country,
            ["import_country_data", "--candidate-dir", "candidate", "--database", "db.sqlite",
             "--approval-id", "resume-country-001"],
            "import_country_data", {"countries": 1},
        ),
        (
            review,
            ["import_review_data", "--database", "db.sqlite", "--iso-reference", "iso.csv",
             "--iso-provenance", "iso.json", "--iso-proposals", "iso.md",
             "--persian-candidates", "fa.json", "--persian-provenance", "fa-provenance.json",
             "--approval-id", "resume-review-001"],
            "import_review_data", {"countries": 1},
        ),
    ],
)
def test_importers_keep_existing_approval_id_recovery_path(
    monkeypatch, module, argv, import_name, expected
):
    monkeypatch.setattr(sys, "argv", argv)
    calls = []

    def importer(*_args, **kwargs):
        calls.append(kwargs)
        return expected

    monkeypatch.setattr(module, import_name, importer)
    result = module.main()

    assert result == 0
    assert calls[0]["approval_id"] == argv[argv.index("--approval-id") + 1]
