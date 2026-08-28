targetScope = 'resourceGroup'

@allowed([
  'francecentral'
])
param location string

param virtualNetworkName string
param virtualNetworkAddressPrefix string
param containerAppsEnvironmentSubnetName string
param containerAppsEnvironmentSubnetPrefix string
param privateEndpointSubnetName string
param privateEndpointSubnetPrefix string
param replacementContainerAppsEnvironmentName string
param postgresqlServerName string
param logAnalyticsWorkspaceName string
param postgresqlPrivateEndpointName string
param postgresqlPrivateLinkConnectionName string
param privateDnsZoneLinkName string
param tags object

resource postgresqlServer 'Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01' existing = {
  name: postgresqlServerName
}

resource logAnalyticsWorkspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' existing = {
  name: logAnalyticsWorkspaceName
}

module developmentNetwork 'modules/unit9-development-network.bicep' = {
  name: 'unit9-development-network'
  params: {
    virtualNetworkName: virtualNetworkName
    location: location
    virtualNetworkAddressPrefix: virtualNetworkAddressPrefix
    containerAppsEnvironmentSubnetName: containerAppsEnvironmentSubnetName
    containerAppsEnvironmentSubnetPrefix: containerAppsEnvironmentSubnetPrefix
    privateEndpointSubnetName: privateEndpointSubnetName
    privateEndpointSubnetPrefix: privateEndpointSubnetPrefix
    tags: tags
  }
}

module postgresqlPrivateConnectivity 'modules/postgresql-private-connectivity.bicep' = {
  name: 'unit9-postgresql-private-connectivity'
  params: {
    privateEndpointName: postgresqlPrivateEndpointName
    privateLinkConnectionName: postgresqlPrivateLinkConnectionName
    privateDnsZoneLinkName: privateDnsZoneLinkName
    location: location
    postgresqlServerId: postgresqlServer.id
    privateEndpointSubnetId: developmentNetwork.outputs.privateEndpointSubnetId
    virtualNetworkId: developmentNetwork.outputs.virtualNetworkId
    tags: tags
  }
}

module replacementContainerAppsEnvironment 'modules/network-capable-container-apps-environment.bicep' = {
  name: 'unit9-replacement-container-apps-environment'
  params: {
    environmentName: replacementContainerAppsEnvironmentName
    location: location
    infrastructureSubnetId: developmentNetwork.outputs.containerAppsEnvironmentSubnetId
    logAnalyticsCustomerId: logAnalyticsWorkspace.properties.customerId
    logAnalyticsSharedKey: logAnalyticsWorkspace.listKeys().primarySharedKey
    tags: tags
  }
}

output virtualNetworkId string = developmentNetwork.outputs.virtualNetworkId
output containerAppsEnvironmentSubnetId string = developmentNetwork.outputs.containerAppsEnvironmentSubnetId
output privateEndpointSubnetId string = developmentNetwork.outputs.privateEndpointSubnetId
output postgresqlPrivateEndpointId string = postgresqlPrivateConnectivity.outputs.privateEndpointId
output postgresqlPrivateDnsZoneId string = postgresqlPrivateConnectivity.outputs.privateDnsZoneId
output replacementContainerAppsEnvironmentId string = replacementContainerAppsEnvironment.outputs.environmentId
