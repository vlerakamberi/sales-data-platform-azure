param logAnalyticsName string
param location string
param retentionDays int
param tags object

resource workspace 'Microsoft.OperationalInsights/workspaces@2025-07-01' = {
  name: logAnalyticsName
  location: location
  tags: tags
  properties: {
    features: {
      enableLogAccessUsingOnlyResourcePermissions: true
    }
    publicNetworkAccessForIngestion: 'Enabled'
    publicNetworkAccessForQuery: 'Enabled'
    retentionInDays: retentionDays
    sku: {
      name: 'PerGB2018'
    }
  }
}

output workspaceId string = workspace.id
output workspaceName string = workspace.name
output customerId string = workspace.properties.customerId
@secure()
output sharedKey string = workspace.listKeys().primarySharedKey
