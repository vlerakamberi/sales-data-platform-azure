@description('Environment-specific transformation workload principal.')
param transformationPrincipalId string

@description('Environment-specific Data Factory system-assigned principal.')
param dataFactoryPrincipalId string

param registryName string
param storageAccountName string
param rawContainerName string
param processedContainerName string
param curatedContainerName string
param quarantineContainerName string
param transformationJobName string

var acrPullRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  '7f951dda-4ed3-4680-a7ca-43fe172d538d'
)
var storageBlobDataContributorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'ba92f5b4-2d11-453d-a403-e96b0029c9fe'
)
var containerAppsJobsOperatorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'b9a307c4-5aa3-4b52-ba60-2b17c136cd7b'
)

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: registryName
}

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

resource transformationJob 'Microsoft.App/jobs@2025-07-01' existing = {
  name: transformationJobName
}

@description('Transformation identity can pull, but never push, images from this environment ACR.')
resource transformationAcrPull 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(registry.id, transformationPrincipalId, acrPullRoleDefinitionId)
  scope: registry
  properties: {
    principalId: transformationPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: acrPullRoleDefinitionId
  }
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

@description('ADF can read, start, and stop only this environment transformation job.')
resource dataFactoryJobOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(transformationJob.id, dataFactoryPrincipalId, containerAppsJobsOperatorRoleDefinitionId)
  scope: transformationJob
  properties: {
    principalId: dataFactoryPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: containerAppsJobsOperatorRoleDefinitionId
  }
}
