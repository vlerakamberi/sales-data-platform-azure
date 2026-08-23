import json
import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
PIPELINE_PATH = ROOT / "orchestration/adf/pipelines/northstar-sales-orchestration.json"
TRIGGER_PATH = ROOT / "orchestration/adf/triggers/northstar-sales-schedule.json"


def _load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _activities() -> dict[str, dict]:
    items = _load(PIPELINE_PATH)["properties"]["activities"]
    return {activity["name"]: activity for activity in items}


def _timespan_seconds(value: str) -> int:
    hours, minutes, seconds = (int(component) for component in value.split(":"))
    return hours * 3600 + minutes * 60 + seconds


def test_exact_development_pipeline_and_governed_raw_contract() -> None:
    pipeline = _load(PIPELINE_PATH)
    assert pipeline["name"] == "nsrsdp-dev-sales-orchestration"
    assert set(pipeline["properties"]["parameters"]) == {
        "dataset",
        "partitionDate",
        "sourceId",
        "sourceObjectId",
        "inputBlob",
        "contractVersion",
        "subscriptionId",
    }
    text = PIPELINE_PATH.read_text(encoding="utf-8").casefold()
    for prohibited in ("github", "sftp", "postgresql", "copyactivity", "dataflow"):
        assert prohibited not in text


def test_exact_arm_start_operation_uses_msi_and_complete_unit7_template() -> None:
    start = _activities()["Start existing Container Apps transformation Job"]
    assert start["type"] == "WebActivity"
    assert start["policy"]["timeout"] == "00:10:00"
    assert start["policy"]["retry"] == 0
    assert start["policy"]["retryIntervalInSeconds"] == 30
    properties = start["typeProperties"]
    assert properties["method"] == "POST"
    assert properties["httpRequestTimeout"] == "00:05:00"
    assert _timespan_seconds(start["policy"]["timeout"]) == 10 * 60
    assert _timespan_seconds(properties["httpRequestTimeout"]) == 5 * 60
    assert _timespan_seconds(start["policy"]["timeout"]) > _timespan_seconds(
        properties["httpRequestTimeout"]
    )
    assert "turnOffAsync" not in properties
    uri = properties["url"]["value"]
    assert uri.endswith(
        "'/resourceGroups/nsrsdp-dev-rg/providers/Microsoft.App/jobs/"
        "nsrsdp-dev-transform-job/start?api-version=2025-07-01')"
    )
    assert properties["authentication"] == {
        "type": "MSI",
        "resource": "https://management.azure.com/",
    }
    body = properties["body"]["value"]
    assert body.count('"containers":[') == 1
    assert body.count('"name":"transformation"') == 1
    assert body.count('"image":') == 1
    assert (
        '"image":"nsrsdpdev2gndgslsp4a6cacr.azurecr.io/'
        'nsrsdp-dev-transformation:unit7-13cd4410b8e2"' in body
    )
    assert '"resources":{"cpu":0.5,"memory":"1Gi"}' in body

    expected_environment = {
        "SDPA_ENVIRONMENT": "development",
        "SDPA_STORAGE_ACCOUNT_URL": ("https://nsrsdpdev2gndgslsp4a6cst.blob.core.windows.net"),
        "SDPA_RAW_CONTAINER": "raw",
        "SDPA_PROCESSED_CONTAINER": "processed",
        "SDPA_CURATED_CONTAINER": "curated",
        "SDPA_QUARANTINE_CONTAINER": "quarantine",
    }
    for name, value in expected_environment.items():
        assert f'{{"name":"{name}","value":"{value}"}}' in body

    for argument in (
        "--input-blob",
        "--dataset",
        "--partition-date",
        "--source-id",
        "--source-object-id",
        "--execution-id",
        "--correlation-id",
        "--contract-version",
    ):
        assert argument in body
    assert "variables('executionId')" in body
    assert "variables('correlationId')" in body

    prohibited = (
        "volumes",
        "initContainers",
        ":latest",
        "placeholder",
        "secret",
        "password",
        "sasToken",
        "accountKey",
        "postgresql",
    )
    for value in prohibited:
        assert value.casefold() not in body.casefold()


def test_identity_dependency_polling_and_terminal_failure_contract() -> None:
    activities = _activities()
    execution = activities["Initialize execution identity"]
    correlation = activities["Initialize correlation identity"]
    start = activities["Start existing Container Apps transformation Job"]
    capture = activities["Capture Container Apps execution identity"]
    poll = activities["Poll managed Job execution to terminal state"]
    outcome = activities["Propagate terminal Job outcome"]
    assert execution["typeProperties"]["value"]["value"] == (
        "@concat('unit8-adf-',pipeline().RunId)"
    )
    assert correlation["typeProperties"]["value"]["value"] == "@pipeline().RunId"
    assert correlation["dependsOn"][0]["activity"] == execution["name"]
    assert start["dependsOn"][0]["activity"] == correlation["name"]
    assert capture["dependsOn"][0]["activity"] == start["name"]
    assert poll["dependsOn"][0]["activity"] == capture["name"]
    assert outcome["dependsOn"][0]["activity"] == poll["name"]
    assert poll["typeProperties"]["timeout"] == "0.00:25:00"
    poll_activities = {
        activity["name"]: activity for activity in poll["typeProperties"]["activities"]
    }
    assert poll_activities["Wait before execution status read"]["typeProperties"] == {
        "waitTimeInSeconds": 15
    }
    status_read_policy = poll_activities["Read Container Apps execution status"]["policy"]
    assert status_read_policy["retry"] == 2
    assert status_read_policy["retryIntervalInSeconds"] == 30
    assert "Succeeded" in poll["typeProperties"]["expression"]["value"]
    assert "Failed" in poll["typeProperties"]["expression"]["value"]
    assert outcome["typeProperties"]["ifTrueActivities"] == []
    assert outcome["typeProperties"]["ifFalseActivities"][0]["type"] == "Fail"
    assert "rejected-is-success" in _load(PIPELINE_PATH)["properties"]["annotations"]


def test_trigger_is_exact_low_frequency_development_and_stopped() -> None:
    trigger = _load(TRIGGER_PATH)
    assert trigger["name"] == "nsrsdp-dev-sales-schedule"
    properties = trigger["properties"]
    assert properties["runtimeState"] == "Stopped"
    assert properties["type"] == "ScheduleTrigger"
    assert properties["typeProperties"]["recurrence"]["frequency"] == "Week"
    assert "development" in properties["annotations"]
    assert properties["pipelines"][0]["pipelineReference"]["referenceName"] == (
        "nsrsdp-dev-sales-orchestration"
    )


def test_bicep_grants_only_job_scoped_container_apps_jobs_operator() -> None:
    rbac = (ROOT / "infrastructure/bicep/modules/adf-orchestration-rbac.bicep").read_text(
        encoding="utf-8"
    )
    assert set(re.findall(r"'[0-9a-f-]{36}'", rbac)) == {"'b9a307c4-5aa3-4b52-ba60-2b17c136cd7b'"}
    assert "scope: transformationJob" in rbac
    assert rbac.count("Microsoft.Authorization/roleAssignments") == 1
    for prohibited in ("Owner", "Contributor", "User Access Administrator", "Storage Blob"):
        assert prohibited not in rbac


def test_unit8_is_existing_resource_only_non_secret_development_overlay() -> None:
    paths = [
        ROOT / "infrastructure/bicep/unit8-adf-orchestration.bicep",
        ROOT / "infrastructure/bicep/modules/adf-orchestration.bicep",
        ROOT / "infrastructure/bicep/modules/adf-orchestration-rbac.bicep",
        ROOT / "infrastructure/bicep/environments/unit8-dev.bicepparam",
        PIPELINE_PATH,
        TRIGGER_PATH,
    ]
    text = "\n".join(path.read_text(encoding="utf-8") for path in paths)
    assert "Microsoft.DataFactory/factories@2018-06-01' existing" in text
    assert "Microsoft.App/jobs@2025-07-01' existing" in text
    assert "nsrsdp-dev-2gndgslsp4a6c-adf" in text
    assert "nsrsdp-dev-transform-job" in text
    for prohibited in (
        "production",
        "staging",
        "postgresql",
        "clientsecret",
        "accountkey",
        "sastoken",
        "bearer ",
        "password",
    ):
        assert prohibited not in text.casefold()
