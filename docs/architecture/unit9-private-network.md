# Unit 9 Development Private Network

Status: **UNIT 9.3 INFRASTRUCTURE DEFINED — NOT DEPLOYED**

Unit 9.3 defines the development-only STATE B network amendment. It performs no Azure operation and
does not change production. The VNet is `10.42.0.0/26` in France Central. No earlier repository
definition used a CIDR, so this RFC1918 range has no inherited repository conflict; environment or
enterprise address coordination remains a deployment prerequisite.

The VNet contains two isolated subnets:

- `10.42.0.0/27` is dedicated to a future Workload Profiles Container Apps Environment and is
  delegated to `Microsoft.App/environments`. `/27` is the supported minimum for this environment
  model and leaves no incentive to reserve a larger development range.
- `10.42.0.32/28` is dedicated to the PostgreSQL Private Endpoint and disables private-endpoint
  network policies. It contains no Container Apps infrastructure or unrelated Unit 9 resource.

The Private Endpoint references the existing governed PostgreSQL Flexible Server through group
`postgresqlServer`; it does not create a server or public fallback. The
`privatelink.postgres.database.azure.com` Private DNS zone is linked to the VNet with registration
disabled and associated with the endpoint through its default DNS zone group. PostgreSQL's
inherited `publicNetworkAccess = Disabled` remains unchanged.

The future replacement `nsrsdp-dev-network-cae` uses the dedicated subnet, the Workload Profiles
environment model, and only the serverless `Consumption` profile. It reuses the existing Log
Analytics workspace. It is an external environment definition because private database egress does
not require private Container Apps ingress; no dedicated always-on profile is defined.

## Migration and lifecycle boundary

Unit 9.3 does not move or recreate the existing Container Apps Job, change ADF references, grant
roles, or delete the legacy Container Apps Environment. Unit 9.4 must explicitly migrate the Job.
If recreation is required, its SystemAssigned principal may change; Unit 9.4 must reconcile every
workload role assignment and the later PostgreSQL Entra mapping before cutover. Legacy environment
deletion remains separately governed Unit 9.7 work.

The definitions create no VNet peering, VPN, Firewall, NAT Gateway, Bastion, custom DNS server, or
other always-on network component. PostgreSQL retains its governed stopped/resting lifecycle; this
unit contains no start operation.
