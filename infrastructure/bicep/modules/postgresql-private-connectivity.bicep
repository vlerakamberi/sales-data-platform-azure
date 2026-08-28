param privateEndpointName string
param privateLinkConnectionName string
param privateDnsZoneLinkName string
param location string
param postgresqlServerId string
param privateEndpointSubnetId string
param virtualNetworkId string
param tags object

var privateDnsZoneName = 'privatelink.postgres.database.azure.com'

resource privateDnsZone 'Microsoft.Network/privateDnsZones@2024-06-01' = {
  name: privateDnsZoneName
  location: 'global'
  tags: tags
}

resource privateDnsZoneLink 'Microsoft.Network/privateDnsZones/virtualNetworkLinks@2024-06-01' = {
  parent: privateDnsZone
  name: privateDnsZoneLinkName
  location: 'global'
  tags: tags
  properties: {
    registrationEnabled: false
    resolutionPolicy: 'Default'
    virtualNetwork: {
      id: virtualNetworkId
    }
  }
}

resource postgresqlPrivateEndpoint 'Microsoft.Network/privateEndpoints@2025-01-01' = {
  name: privateEndpointName
  location: location
  tags: tags
  properties: {
    subnet: {
      id: privateEndpointSubnetId
    }
    privateLinkServiceConnections: [
      {
        name: privateLinkConnectionName
        properties: {
          privateLinkServiceId: postgresqlServerId
          groupIds: [
            'postgresqlServer'
          ]
          requestMessage: 'Unit 9 development PostgreSQL private connectivity'
        }
      }
    ]
  }
}

resource privateDnsZoneGroup 'Microsoft.Network/privateEndpoints/privateDnsZoneGroups@2025-01-01' = {
  parent: postgresqlPrivateEndpoint
  name: 'default'
  properties: {
    privateDnsZoneConfigs: [
      {
        name: 'postgresql-private-dns-zone'
        properties: {
          privateDnsZoneId: privateDnsZone.id
        }
      }
    ]
  }
}

output privateEndpointId string = postgresqlPrivateEndpoint.id
output privateDnsZoneId string = privateDnsZone.id
output privateDnsZoneLinkId string = privateDnsZoneLink.id
output privateDnsZoneGroupId string = privateDnsZoneGroup.id
