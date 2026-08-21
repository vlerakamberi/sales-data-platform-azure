param keyVaultName string
param location string
param tags object

resource keyVault 'Microsoft.KeyVault/vaults@2024-11-01' = {
  name: keyVaultName
  location: location
  tags: tags
  properties: {
    tenantId: tenant().tenantId
    sku: {
      family: 'A'
      name: 'standard'
    }
    enableRbacAuthorization: true
    enablePurgeProtection: true
    enableSoftDelete: true
    publicNetworkAccess: 'Enabled'
    softDeleteRetentionInDays: 90
  }
}

output keyVaultId string = keyVault.id
output keyVaultName string = keyVault.name
output vaultUri string = keyVault.properties.vaultUri
