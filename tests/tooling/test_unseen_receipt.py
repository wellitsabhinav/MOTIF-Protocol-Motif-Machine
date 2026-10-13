"""A partial, failed or stale receipt must never enable physical work."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tools.unseen_receipt import validate


@pytest.fixture
def receipt():
    return json.loads(Path("experiments/temporal_qualification/unseen/logical_result.json").read_text())


def test_complete_unseen_receipt(receipt):
    assert validate(receipt)["total_compared_cycles"] > 0


@pytest.mark.parametrize("mutation", [
    "truncated", "duplicate", "model_only", "incomplete", "disagreement", "oracle_missing",
    "oracle_failure", "early_token", "stale_configuration", "wrong_total", "missing_artifact", "wrong_expected",
    "oracle_negative_incomplete", "invalid_artifact_digest",
])
def test_bad_unseen_receipt_is_rejected(receipt, mutation):
    invalid = deepcopy(receipt)
    first = invalid["cases"][0]
    if mutation == "truncated":
        invalid["cases"].pop()
    elif mutation == "duplicate":
        invalid["cases"][-1] = deepcopy(first)
    elif mutation == "model_only":
        invalid["model_only"] = True
    elif mutation == "incomplete":
        invalid["qualification_complete"] = False
    elif mutation == "disagreement":
        first["model_rtl_agreement"] = False
    elif mutation == "oracle_missing":
        first.pop("oracle")
    elif mutation == "oracle_failure":
        first["oracle"]["errors"].append({"code": "missing_token"})
    elif mutation == "early_token":
        first["oracle"]["observed_acceptances"][0]["cycle"] = first["oracle"]["expected"][0]["earliest"] - 1
    elif mutation == "stale_configuration":
        invalid["configuration_sha256_lf"] = "0" * 64
    elif mutation == "wrong_total":
        invalid["total_compared_cycles"] -= 1
    elif mutation == "missing_artifact":
        first["evidence_sha256_lf"].pop("rtl.jsonl")
    elif mutation == "wrong_expected":
        first["expected"] = []
    elif mutation == "oracle_negative_incomplete":
        negative = next(case for case in invalid["cases"] if not case["expected"])
        negative["oracle"].pop("expected")
    elif mutation == "invalid_artifact_digest":
        first["evidence_sha256_lf"]["rtl.jsonl"] = None
    with pytest.raises(ValueError):
        validate(invalid)
