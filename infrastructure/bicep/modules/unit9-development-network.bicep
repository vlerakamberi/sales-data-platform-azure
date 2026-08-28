param virtualNetworkName string
param location string
param virtualNetworkAddressPrefix string
param containerAppsEnvironmentSubnetName string
param containerAppsEnvironmentSubnetPrefix string
param privateEndpointSubnetName string
param privateEndpointSubnetPrefix string
param tags object

resource virtualNetwork 'Microsoft.Network/virtualNetworks@2025-01-01' = {
  name: virtualNetworkName
  location: location
  tags: tags
  properties: {
    addressSpace: {
      addressPrefixes: [
        virtualNetworkAddressPrefix
      ]
    }
  }
}

resource containerAppsEnvironmentSubnet 'Microsoft.Network/virtualNetworks/subnets@2025-01-01' = {
  parent: virtualNetwork
  name: containerAppsEnvironmentSubnetName
  properties: {
    addressPrefix: containerAppsEnvironmentSubnetPrefix
    delegations: [
      {
        name: 'container-apps-environment-delegation'
        properties: {
          serviceName: 'Microsoft.App/environments'
        }
      }
    ]
  }
}

resource privateEndpointSubnet 'Microsoft.Network/virtualNetworks/subnets@2025-01-01' = {
  parent: virtualNetwork
  name: privateEndpointSubnetName
  properties: {
    addressPrefix: privateEndpointSubnetPrefix
    privateEndpointNetworkPolicies: 'Disabled'
  }
}

output virtualNetworkId string = virtualNetwork.id
output containerAppsEnvironmentSubnetId string = containerAppsEnvironmentSubnet.id
output privateEndpointSubnetId string = privateEndpointSubnet.id
