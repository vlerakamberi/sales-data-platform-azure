@description('Environment-specific transformation workload principal.')
param transformationPrincipalId string

param storageAccountName string
param rawContainerName string
param processedContainerName string
param curatedContainerName string
param quarantineContainerName string

var storageBlobDataContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageAccountName
}

resource blobService 'Microsoft.Storage/storageAccounts/blobServices@2025-06-01' existing = {
  parent: storageAccount
  name: 'default'
}

resource rawContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' existing = {
  parent: blobService
  name: rawContainerName
}

resource processedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' existing = {
  parent: blobService
  name: processedContainerName
}

resource curatedContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' existing = {
  parent: blobService
  name: curatedContainerName
}

resource quarantineContainer 'Microsoft.Storage/storageAccounts/blobServices/containers@2025-06-01' existing = {
  parent: blobService
  name: quarantineContainerName
}


@description('Data-plane role at the raw container; application policy remains read-only.')
resource transformationRawData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(rawContainer.id, transformationPrincipalId, storageBlobDataContributorRoleDefinitionId)
  scope: rawContainer
  properties: {
    principalId: transformationPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
  }
}

@description('Transformation identity can write governed processed objects in this container.')
resource transformationProcessedData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(processedContainer.id, transformationPrincipalId, storageBlobDataContributorRoleDefinitionId)
  scope: processedContainer
  properties: {
    principalId: transformationPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
  }
}

@description('Transformation identity can write accepted objects in this curated container.')
resource transformationCuratedData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(curatedContainer.id, transformationPrincipalId, storageBlobDataContributorRoleDefinitionId)
  scope: curatedContainer
  properties: {
    principalId: transformationPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
  }
}

@description('Transformation identity can write rejected objects in this quarantine container.')
resource transformationQuarantineData 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(quarantineContainer.id, transformationPrincipalId, storageBlobDataContributorRoleDefinitionId)
  scope: quarantineContainer
  properties: {
    principalId: transformationPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: storageBlobDataContributorRoleDefinitionId
  }
}
