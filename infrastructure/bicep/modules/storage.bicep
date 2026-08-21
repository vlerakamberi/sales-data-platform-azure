@description('Globally unique StorageV2 account name.')
param storageAccountName string

param location string

@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_ZRS'
])
param skuName string

param deleteRetentionDays int
param rawCoolAfterDays int
param derivedDataDeleteAfterDays int
param tags object

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' = {
  name: storageAccountName
  location: location
  tags: tags
  sku: {
    name: skuName
  }
  kind: 'StorageV2'
  properties: {
    allowBlobPublicAccess: false
    allowCrossTenantReplication: false
    allowSharedKeyAccess: false
    defaultToOAuthAuthentication: true
    isHnsEnabled: true
    minimumTlsVersion: 'TLS1_2'
    publicNetworkAccess: 'Enabled'
    supportsHttpsTrafficOnly: true
  }
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    containerDeleteRetentionPolicy: {
      enabled: true
      days: deleteRetentionDays
    }
    deleteRetentionPolicy: {
      enabled: true
      days: deleteRetentionDays
    }
  }
}

resource rawContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'raw'
  properties: {
    publicAccess: 'None'
  }
}

resource processedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'processed'
  properties: {
    publicAccess: 'None'
  }
}

resource curatedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'curated'
  properties: {
    publicAccess: 'None'
  }
}

resource quarantineContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' = {
  parent: blobService
  name: 'quarantine'
  properties: {
    publicAccess: 'None'
  }
}

resource lifecyclePolicy 'Microsoft.Storage/storageAccounts/managementPolicies@2025-06-01' = {
  parent: storageAccount
  name: 'default'
  properties: {
    policy: {
      rules: [
        {
          name: 'cool-append-oriented-raw-data'
          enabled: true
          type: 'Lifecycle'
          definition: {
            actions: {
              baseBlob: {
                tierToCool: {
                  daysAfterModificationGreaterThan: rawCoolAfterDays
                }
              }
            }
            filters: {
              blobTypes: [
                'blockBlob'
              ]
              prefixMatch: [
                'raw/'
              ]
            }
          }
        }
        {
          name: 'expire-reproducible-derived-data'
          enabled: true
          type: 'Lifecycle'
          definition: {
            actions: {
              baseBlob: {
                delete: {
                  daysAfterModificationGreaterThan: derivedDataDeleteAfterDays
                }
              }
            }
            filters: {
              blobTypes: [
                'blockBlob'
                'appendBlob'
              ]
              prefixMatch: [
                'processed/'
                'curated/'
                'quarantine/'
              ]
            }
          }
        }
      ]
    }
  }
}

output storageAccountId string = storageAccount.id
output storageAccountName string = storageAccount.name
output blobEndpoint string = storageAccount.properties.primaryEndpoints.blob
output dfsEndpoint string = storageAccount.properties.primaryEndpoints.dfs
output rawContainerName string = rawContainer.name
output processedContainerName string = processedContainer.name
output curatedContainerName string = curatedContainer.name
output quarantineContainerName string = quarantineContainer.name
