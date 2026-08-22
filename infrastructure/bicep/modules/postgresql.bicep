param serverName string
param location string
param skuName string

@allowed([
  'Burstable'
  'GeneralPurpose'
])
param skuTier string

param storageSizeGb int
param backupRetentionDays int

@allowed([
  'Enabled'
  'Disabled'
])
param geoRedundantBackup string

param tags object

resource server 'Microsoft.DBforPostgreSQL/flexibleServers@2025-08-01' = {
  name: serverName
  location: location
  tags: tags
  sku: {
    name: skuName
    tier: skuTier
  }
  properties: {
    authConfig: {
      activeDirectoryAuth: 'Enabled'
      passwordAuth: 'Disabled'
      tenantId: tenant().tenantId
    }
    backup: {
      backupRetentionDays: backupRetentionDays
      geoRedundantBackup: geoRedundantBackup
    }
    createMode: 'Default'
    dataEncryption: {
      type: 'SystemManaged'
    }
    highAvailability: {
      mode: 'Disabled'
    }
    network: {
      publicNetworkAccess: 'Disabled'
    }
    storage: {
      autoGrow: 'Enabled'
      storageSizeGB: storageSizeGb
    }
    version: '17'
  }
}

output serverId string = server.id
output serverName string = server.name
output fullyQualifiedDomainName string = server.properties.fullyQualifiedDomainName
