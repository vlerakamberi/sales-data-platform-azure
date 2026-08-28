import hashlib
import ipaddress
from pathlib import Path

ROOT = Path(__file__).parents[2]
BICEP = ROOT / "infrastructure" / "bicep"


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_unit9_uses_one_minimal_development_vnet_with_distinct_subnets() -> None:
    parameters = _read("infrastructure/bicep/environments/unit9-dev.bicepparam")
    network = _read("infrastructure/bicep/modules/unit9-development-network.bicep")
    composition = _read("infrastructure/bicep/unit9-private-network.bicep")

    vnet = ipaddress.ip_network("10.42.0.0/26")
    cae = ipaddress.ip_network("10.42.0.0/27")
    private_endpoint = ipaddress.ip_network("10.42.0.32/28")
    assert cae.subnet_of(vnet)
    assert private_endpoint.subnet_of(vnet)
    assert not cae.overlaps(private_endpoint)
    assert "param location = 'francecentral'" in parameters
    assert parameters.count("param virtualNetworkName") == 1
    assert network.count("Microsoft.Network/virtualNetworks@") == 1
    assert "Microsoft.Network/virtualNetworks" not in composition
    for prohibited in ("peerings", "natGateways", "bastionHosts", "azureFirewalls", "vpnGateways"):
        assert prohibited not in network


def test_cae_and_private_endpoint_subnet_contracts_are_isolated() -> None:
    network = _read("infrastructure/bicep/modules/unit9-development-network.bicep")
    assert "serviceName: 'Microsoft.App/environments'" in network
    assert "privateEndpointNetworkPolicies: 'Disabled'" in network
    cae_section, private_endpoint_section = network.split(
        "resource privateEndpointSubnet", maxsplit=1
    )
    assert "delegations:" in cae_section
    assert "privateEndpointNetworkPolicies" not in cae_section
    assert "delegations:" not in private_endpoint_section


def test_postgresql_private_link_and_dns_are_exact_and_private_only() -> None:
    connectivity = _read("infrastructure/bicep/modules/postgresql-private-connectivity.bicep")
    composition = _read("infrastructure/bicep/unit9-private-network.bicep")
    inherited_server = _read("infrastructure/bicep/modules/postgresql.bicep")

    assert "Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01' existing" in composition
    assert "Microsoft.DBforPostgreSQL/flexibleServers@" not in connectivity
    assert "Microsoft.Network/privateEndpoints@2025-01-01" in connectivity
    assert "'postgresqlServer'" in connectivity
    assert "'privatelink.postgres.database.azure.com'" in connectivity
    assert "privateDnsZones/virtualNetworkLinks@2024-06-01" in connectivity
    assert "privateEndpoints/privateDnsZoneGroups@2025-01-01" in connectivity
    assert "registrationEnabled: false" in connectivity
    assert "publicNetworkAccess: 'Disabled'" in inherited_server
    assert "firewallRules" not in connectivity


def test_replacement_cae_is_vnet_integrated_consumption_and_reuses_logs() -> None:
    replacement = _read(
        "infrastructure/bicep/modules/network-capable-container-apps-environment.bicep"
    )
    composition = _read("infrastructure/bicep/unit9-private-network.bicep")
    parameters = _read("infrastructure/bicep/environments/unit9-dev.bicepparam")

    assert "infrastructureSubnetId: infrastructureSubnetId" in replacement
    assert "workloadProfiles:" in replacement
    assert "name: 'Consumption'" in replacement
    assert "workloadProfileType: 'Consumption'" in replacement
    assert "minimumCount" not in replacement
    assert "maximumCount" not in replacement
    assert "logAnalyticsWorkspace" in composition
    assert "logAnalyticsWorkspace.listKeys().primarySharedKey" in composition
    assert "replacementContainerAppsEnvironmentName = 'nsrsdp-dev-network-cae'" in parameters
    assert "nsrsdp-dev-cae'" not in parameters


def test_unit9_has_no_job_adf_rbac_sql_or_lifecycle_cutover() -> None:
    unit9_text = "\n".join(
        path.read_text(encoding="utf-8")
        for path in (
            BICEP / "unit9-private-network.bicep",
            BICEP / "environments" / "unit9-dev.bicepparam",
            BICEP / "modules" / "unit9-development-network.bicep",
            BICEP / "modules" / "postgresql-private-connectivity.bicep",
            BICEP / "modules" / "network-capable-container-apps-environment.bicep",
        )
    )
    for prohibited in (
        "Microsoft.App/jobs",
        "Microsoft.DataFactory",
        "Microsoft.Authorization/roleAssignments",
        "container-apps-job.bicep",
        "delete",
        "migration",
        "sql/migrations",
    ):
        assert prohibited.casefold() not in unit9_text.casefold()


def test_frozen_job_adf_and_sql_artifacts_are_unchanged() -> None:
    expected = {
        "infrastructure/bicep/modules/container-apps-job.bicep": (
            "f2aea0f990dfa903f58f76b0a907535b55b4b34df97aca22a47d6fc26644e3bd"
        ),
        "orchestration/adf/pipelines/northstar-sales-orchestration.json": (
            "1a338e3454b38f0d80743cfcd9beda823be28601fefbb5cfec95238b2f0b8fa7"
        ),
        "orchestration/adf/triggers/northstar-sales-schedule.json": (
            "26d21fdc855cf6c0451d68a2491ee34b0ef9d72c93bd6458eec4fe6417b5f004"
        ),
        "sql/migrations/V001__create_relational_serving_foundation.sql": (
            "c17e87cd08ea8927e37cf58eda536e0bd69274e838cd17b3b0830709bd630e97"
        ),
    }
    for path, digest in expected.items():
        assert hashlib.sha256((ROOT / path).read_bytes()).hexdigest() == digest
