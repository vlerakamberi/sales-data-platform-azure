targetScope = 'resourceGroup'

param location string
param acrName string
param acrLoginServer string
param managedEnvironmentName string
param storageAccountName string
param jobName string
param acrPullIdentityName string
param imageName string
param environmentName string
param rawContainerName string
param processedContainerName string
param curatedContainerName string
param quarantineContainerName string
param cpu string
param memory string
param tags object

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: acrName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageAccountName
}

resource managedEnvironment 'Microsoft.App/managedEnvironments@2025-07-01' existing = {
  name: managedEnvironmentName
}

module acrPullIdentity 'modules/acr-pull-identity.bicep' = {
  name: 'unit7-acr-pull-identity'
  params: {
    identityName: acrPullIdentityName
    location: location
    registryName: registry.name
    tags: tags
  }
}

module transformationJob 'modules/container-apps-job.bicep' = {
  name: 'unit7-transformation-job'
  params: {
    jobName: jobName
    location: location
    managedEnvironmentId: managedEnvironment.id
    registryServer: acrLoginServer
    registryIdentityId: acrPullIdentity.outputs.identityId
    imageName: '${acrLoginServer}/${imageName}'
    environmentName: environmentName
    storageAccountName: storageAccount.name
    rawContainerName: rawContainerName
    processedContainerName: processedContainerName
    curatedContainerName: curatedContainerName
    quarantineContainerName: quarantineContainerName
    cpu: cpu
    memory: memory
    tags: tags
  }
}

module workloadStorageRbac 'modules/identity-rbac.bicep' = {
  name: 'unit7-workload-storage-rbac'
  params: {
    transformationPrincipalId: transformationJob.outputs.principalId
    storageAccountName: storageAccount.name
    rawContainerName: rawContainerName
    processedContainerName: processedContainerName
    curatedContainerName: curatedContainerName
    quarantineContainerName: quarantineContainerName
  }
}

output jobId string = transformationJob.outputs.jobId
output jobPrincipalId string = transformationJob.outputs.principalId
output acrPullIdentityId string = acrPullIdentity.outputs.identityId
output acrPullIdentityPrincipalId string = acrPullIdentity.outputs.principalId
