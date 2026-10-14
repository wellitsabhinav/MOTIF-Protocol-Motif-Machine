"""Read identified physical job snapshots; never dispatch or qualify a run."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, HTTPRedirectHandler, build_opener, urlopen

from tools.v3_physical import preflight, write

REPOSITORY = "wellitsabhinav/MOTIF-Protocol-Motif-Machine"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, message, headers, url):
        return None


def download(suffix, token):
    request = Request("https://api.github.com/repos/" + REPOSITORY + "/" + suffix,
                      headers={"Authorization": "Bearer " + token,
                               "Accept": "application/vnd.github+json",
                               "X-GitHub-Api-Version": "2026-03-10"})
    try:
        with build_opener(NoRedirect).open(request, timeout=30) as response:
            return response.read()
    except HTTPError as error:
        if error.code not in (301, 302, 303, 307, 308):
            raise
        location = error.headers["Location"]
        if urlsplit(location).scheme != "https":
            raise ValueError("Job-log redirect is not HTTPS")
        # Signed log downloads need no GitHub bearer token. Never forward it.
        with urlopen(location, timeout=60) as response:
            return response.read()


def collect(row, output, get):
    identities = preflight(row["source_sha"])
    run_bytes = get("actions/runs/" + str(row["run_id"]))
    run = json.loads(run_bytes)
    if (run["id"] != row["run_id"] or run["head_sha"] != row["source_sha"]
            or run["path"] != ".github/workflows/gds.yml" or run["run_attempt"] != 1):
        raise ValueError("Snapshot identifies another run/source or a rerun")
    jobs_bytes = get("actions/runs/" + str(row["run_id"]) + "/jobs?per_page=100")
    jobs = json.loads(jobs_bytes)
    if jobs["total_count"] > len(jobs["jobs"]):
        raise ValueError("Incomplete job metadata inventory")
    output.mkdir(parents=True, exist_ok=False)
    files = {"workflow.json": run_bytes, "jobs.json": jobs_bytes}
    observations = []
    for job in jobs["jobs"]:
        if job["name"] != "gds":
            continue
        if job["run_id"] != run["id"] or job["head_sha"] != run["head_sha"]:
            raise ValueError("Job source differs from identified physical run")
        observation = {"job_id": job["id"], "status": job["status"], "conclusion": job["conclusion"]}
        try:
            body = get("actions/jobs/" + str(job["id"]) + "/logs")
            name = "job_" + str(job["id"]) + ".log"
            files[name] = body
            observation.update(log_available=True, log_file=name, log_bytes=len(body))
        except HTTPError as error:
            observation.update(log_available=False, log_http_status=error.code)
        observations.append(observation)
    for name, raw in files.items():
        (output / name).write_bytes(raw)
    receipt = {"schema_version": 3, "kind": "read_only_physical_job_snapshot",
               "captured_at_utc": datetime.now(timezone.utc).isoformat(),
               "workflow_run_id": run["id"], "source_sha": run["head_sha"],
               "workflow_status": run["status"], "workflow_conclusion": run["conclusion"],
               "frozen_manifest_sha256_lf": identities["frozen_manifest_sha256_lf"],
               "preregistration": identities["preregistration"], "jobs": observations,
               "files_sha256_raw": {name: hashlib.sha256(raw).hexdigest() for name, raw in files.items()},
               "scope": "Job metadata and downloaded log contents only; active logs may be partial; no latest-stage, final metric, archive correspondence or physical qualification claim"}
    write(output / "snapshot.json", receipt)
    print("SNAPSHOT", run["id"], run["status"], observations)
    return receipt


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--request", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get("GITHUB_REPOSITORY") != REPOSITORY:
        raise ValueError("Snapshot collector is restricted to its identified repository")
    token = os.environ["GH_TOKEN"]
    for row in json.loads(args.request.read_text())["runs"]:
        collect(row, args.output / str(row["run_id"]), lambda suffix: download(suffix, token))


if __name__ == "__main__":
    main()
