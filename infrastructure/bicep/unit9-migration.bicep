targetScope = 'resourceGroup'

param location string
param replacementContainerAppsEnvironmentName string
param replacementJobName string
param acrName string
param acrPullIdentityName string
param imageName string
param environmentName string
param storageAccountName string
param rawContainerName string
param processedContainerName string
param curatedContainerName string
param quarantineContainerName string
param cpu string
param memory string
param tags object

resource replacementContainerAppsEnvironment 'Microsoft.App/managedEnvironments@2025-07-01' existing = {
  name: replacementContainerAppsEnvironmentName
}

resource registry 'Microsoft.ContainerRegistry/registries@2025-04-01' existing = {
  name: acrName
}

resource acrPullIdentity 'Microsoft.ManagedIdentity/userAssignedIdentities@2024-11-30' existing = {
  name: acrPullIdentityName
}

resource storageAccount 'Microsoft.Storage/storageAccounts@2025-06-01' existing = {
  name: storageAccountName
}

module replacementTransformationJob 'modules/container-apps-job.bicep' = {
  name: 'unit9-replacement-transformation-job'
  params: {
    jobName: replacementJobName
    location: location
    managedEnvironmentId: replacementContainerAppsEnvironment.id
    registryServer: registry.properties.loginServer
    registryIdentityId: acrPullIdentity.id
    imageName: '${registry.properties.loginServer}/${imageName}'
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

module replacementWorkloadStorageRbac 'modules/identity-rbac.bicep' = {
  name: 'unit9-replacement-workload-storage-rbac'
  params: {
    transformationPrincipalId: replacementTransformationJob.outputs.principalId
    storageAccountName: storageAccount.name
    rawContainerName: rawContainerName
    processedContainerName: processedContainerName
    curatedContainerName: curatedContainerName
    quarantineContainerName: quarantineContainerName
  }
}

output replacementJobId string = replacementTransformationJob.outputs.jobId
output replacementTransformationJobName string = replacementTransformationJob.outputs.jobName
output replacementJobPrincipalId string = replacementTransformationJob.outputs.principalId
