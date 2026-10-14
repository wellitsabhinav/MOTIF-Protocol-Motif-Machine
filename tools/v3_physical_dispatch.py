"""Dispatch one preregistered physical attempt through the normal CI job token.

Never retries a POST. Existing runs, moved refs or mismatched intents block a
duplicate launch. The pinned GDS workflow and its source remain unchanged.
"""
import argparse
import json
import os
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

from tools.v3_inventory import sha
from tools.v3_physical import preflight, DIRECTORY, write

REPOSITORY = "wellitsabhinav/MOTIF-Protocol-Motif-Machine"


def launch(request, api):
    number, source, branch = request["attempt"], request["source_sha"], request["branch"]
    if type(number) is not int or not 1 <= number <= 3:
        raise ValueError("Physical attempt limit exceeded")
    path = DIRECTORY / f"attempt_{number}_intent.json"
    intent = json.loads(path.read_text())
    if (sha(path.read_bytes()) != request["intent_sha256_lf"] or intent["source_sha"] != source
            or intent["attempt"] != number or intent["status"] != "prepared_before_dispatch"):
        raise ValueError("Dispatch request differs from immutable intent")
    actual = preflight(source)
    if any(actual[key] != intent[key] for key in actual):
        raise ValueError("Identified source/settings differ from prepared intent")
    evidence = {key: actual[key] for key in ("frozen_manifest_sha256_lf", "preregistration")}
    if number > 1:
        previous = json.loads((DIRECTORY / f"attempt_{number-1}_result.json").read_text())
        dispatch = json.loads((DIRECTORY / f"attempt_{number-1}_dispatch.json").read_text())
        if (previous["physical_qualified"] is not False or previous["workflow_status"] != "completed"
                or previous["workflow_run_id"] != dispatch["run_id"] or previous["source_sha"] != dispatch["source_sha"]):
            raise ValueError("Prior physical attempt is not a retained completed failure")
        diagnosis = Path(intent["diagnosis"]["path"])
        if sha(diagnosis.read_bytes()) != intent["diagnosis"]["sha256_lf"]:
            raise ValueError("Prerevision diagnosis changed")
    ref = api("GET", "git/ref/heads/" + quote(branch, safe="/"))
    if ref["object"]["sha"] != source:
        raise ValueError("Physical dispatch branch moved from its exact prepared source")
    runs = api("GET", "actions/runs?head_sha=" + source + "&per_page=100")
    if runs["total_count"] > 100:
        raise ValueError("Incomplete run inventory; refusing dispatch")
    existing = [run for run in runs["workflow_runs"] if run["path"] == ".github/workflows/gds.yml"]
    if existing:
        if len(existing) != 1 or existing[0].get("run_attempt") != 1:
            raise ValueError("Multiple physical runs or reruns require attempt-policy investigation")
        return {"schema_version": 3, "attempt": number, "source_sha": source, **evidence,
                "dispatched": False, "reason": "An official physical run already exists for this source",
                "workflow_run_id": existing[0]["id"], "html_url": existing[0]["html_url"]}
    response = api("POST", "actions/workflows/gds.yml/dispatches",
                   {"ref": branch, "return_run_details": True})
    # A successful older API response can be empty. Never repeat the POST to
    # obtain an identity: preserve acceptance and resolve by reading run metadata.
    return {"schema_version": 3, "attempt": number, "source_sha": source, **evidence,
            "intent_sha256_lf": request["intent_sha256_lf"], "dispatched": True,
            "workflow_run_id": response.get("workflow_run_id"),
            "html_url": response.get("html_url"), "api_response": response,
            "scope": "Accepted dispatch only; qualification requires actual official run metadata and gates"}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise ValueError("Dispatch helper is restricted to its authorized repository")
    token = os.environ["GH_TOKEN"]
    def api(method, suffix, data=None):
        req = Request("https://api.github.com/repos/" + REPOSITORY + "/" + suffix,
                      data=json.dumps(data).encode() if data is not None else None,
                      method=method, headers={"Authorization": "Bearer " + token,
                      "Accept": "application/vnd.github+json", "X-GitHub-Api-Version": "2026-03-10",
                      "Content-Type": "application/json"})
        with urlopen(req, timeout=30) as response:
            body = response.read()
            return json.loads(body) if body else {}
    result = launch(json.loads(args.request.read_text()), api)
    write(args.output, result)
    print("DISPATCH" if result["dispatched"] else "EXISTING", result["workflow_run_id"], result["html_url"])


if __name__ == "__main__":
    main()
