param dataFactoryName string
param location string
param tags object

resource dataFactory 'Microsoft.DataFactory/factories@2018-06-01' = {
  name: dataFactoryName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    publicNetworkAccess: 'Enabled'
  }
}

output dataFactoryId string = dataFactory.id
output dataFactoryName string = dataFactory.name
output principalId string = dataFactory.identity.principalId
