targetScope = 'subscription'

@description('Deployment environment. Only development and production are supported.')
@allowed([
  'development'
  'production'
])
param environment string

@description('Azure region for the environment resource group and resources.')
param location string

@description('Short lowercase workload prefix used in deterministic resource names.')
@minLength(3)
@maxLength(8)
param namingPrefix string

@description('Non-sensitive governance tags added to every supported resource.')
param governanceTags object

@description('Storage account replication SKU.')
@allowed([
  'Standard_LRS'
  'Standard_GRS'
  'Standard_ZRS'
])
param storageSku string

@description('Soft-delete retention for blobs and containers.')
@minValue(1)
@maxValue(365)
param storageDeleteRetentionDays int

@description('Age after which raw blobs move to the cool tier; raw data is not deleted.')
@minValue(1)
param rawCoolAfterDays int

@description('Age after which non-raw data may be deleted by lifecycle policy.')
@minValue(1)
param derivedDataDeleteAfterDays int

@description('Container Registry SKU.')
@allowed([
  'Basic'
  'Standard'
])
param containerRegistrySku string

@description('Log Analytics retention period.')
@minValue(30)
@maxValue(730)
param logRetentionDays int

@description('Container Apps Job CPU allocation.')
param jobCpu string

@description('Container Apps Job memory allocation.')
param jobMemory string

@description('Container image interface for the future transformation runtime.')
param transformationImage string

@description('Deploy the transformation Container Apps Job after its image and pull authorization exist.')
param deployTransformationJob bool

@description('PostgreSQL compute SKU.')
param postgresqlSkuName string

@description('PostgreSQL compute tier.')
@allowed([
  'Burstable'
  'GeneralPurpose'
])
param postgresqlSkuTier string

@description('PostgreSQL storage size in GiB.')
@minValue(32)
param postgresqlStorageSizeGb int

@description('PostgreSQL backup retention in days.')
@minValue(7)
@maxValue(35)
param postgresqlBackupRetentionDays int

var environmentCode = environment == 'development' ? 'dev' : 'prod'
var uniqueSuffix = uniqueString(subscription().id, environment, location)
var resourceGroupName = '${namingPrefix}-${environmentCode}-rg'
var standardTags = union(governanceTags, {
  environment: environment
  managedBy: 'Bicep'
  repository: 'sales-data-platform-azure'
  workload: 'northstar-retail-sales-data-platform'
})
var storageAccountName = take('${namingPrefix}${environmentCode}${uniqueSuffix}st', 24)
var dataFactoryName = take('${namingPrefix}-${environmentCode}-${uniqueSuffix}-adf', 63)
var registryName = take('${namingPrefix}${environmentCode}${uniqueSuffix}acr', 50)
var logAnalyticsName = take('${namingPrefix}-${environmentCode}-${uniqueSuffix}-law', 63)
var containerAppsEnvironmentName = take('${namingPrefix}-${environmentCode}-cae', 60)
var containerAppsJobName = take('${namingPrefix}-${environmentCode}-transform-job', 32)
var keyVaultName = take('${namingPrefix}-${environmentCode}-${uniqueSuffix}-kv', 24)
var postgresqlServerName = take('${namingPrefix}-${environmentCode}-${uniqueSuffix}-pg', 63)

resource platformResourceGroup 'Microsoft.Resources/resourceGroups@2025-04-01' = {
  name: resourceGroupName
  location: location
  tags: standardTags
}

module monitoring 'modules/monitoring.bicep' = {
  name: 'monitoring-${environmentCode}'
  scope: platformResourceGroup
  params: {
    location: location
    logAnalyticsName: logAnalyticsName
    retentionDays: logRetentionDays
    tags: standardTags
  }
}

module storage 'modules/storage.bicep' = {
  name: 'storage-${environmentCode}'
  scope: platformResourceGroup
  params: {
    location: location
    storageAccountName: storageAccountName
    skuName: storageSku
    deleteRetentionDays: storageDeleteRetentionDays
    rawCoolAfterDays: rawCoolAfterDays
    derivedDataDeleteAfterDays: derivedDataDeleteAfterDays
    tags: standardTags
  }
}

module dataFactory 'modules/data-factory.bicep' = {
  name: 'data-factory-${environmentCode}'
  scope: platformResourceGroup
  params: {
    dataFactoryName: dataFactoryName
    location: location
    tags: standardTags
  }
}

module registry 'modules/container-registry.bicep' = {
  name: 'container-registry-${environmentCode}'
  scope: platformResourceGroup
  params: {
    registryName: registryName
    location: location
    skuName: containerRegistrySku
    tags: standardTags
  }
}

module containerAppsEnvironment 'modules/container-apps-environment.bicep' = {
  name: 'container-apps-environment-${environmentCode}'
  scope: platformResourceGroup
  params: {
    environmentName: containerAppsEnvironmentName
    location: location
    logAnalyticsCustomerId: monitoring.outputs.customerId
    logAnalyticsSharedKey: monitoring.outputs.sharedKey
    tags: standardTags
  }
}

module transformationJob 'modules/container-apps-job.bicep' = if (deployTransformationJob) {
  name: 'container-apps-job-${environmentCode}'
  scope: platformResourceGroup
  params: {
    jobName: containerAppsJobName
    location: location
    managedEnvironmentId: containerAppsEnvironment.outputs.environmentId
    registryServer: registry.outputs.loginServer
    imageName: '${registry.outputs.loginServer}/${transformationImage}'
    environmentName: environment
    storageAccountName: storage.outputs.storageAccountName
    rawContainerName: storage.outputs.rawContainerName
    processedContainerName: storage.outputs.processedContainerName
    curatedContainerName: storage.outputs.curatedContainerName
    quarantineContainerName: storage.outputs.quarantineContainerName
    cpu: jobCpu
    memory: jobMemory
    tags: standardTags
  }
}

module keyVault 'modules/key-vault.bicep' = {
  name: 'key-vault-${environmentCode}'
  scope: platformResourceGroup
  params: {
    keyVaultName: keyVaultName
    location: location
    tags: standardTags
  }
}

module postgresql 'modules/postgresql.bicep' = {
  name: 'postgresql-${environmentCode}'
  scope: platformResourceGroup
  params: {
    serverName: postgresqlServerName
    location: location
    skuName: postgresqlSkuName
    skuTier: postgresqlSkuTier
    storageSizeGb: postgresqlStorageSizeGb
    backupRetentionDays: postgresqlBackupRetentionDays
    geoRedundantBackup: environment == 'production' ? 'Enabled' : 'Disabled'
    tags: standardTags
  }
}

module identityRbac 'modules/identity-rbac.bicep' = if (deployTransformationJob) {
  name: 'identity-rbac-${environmentCode}'
  scope: platformResourceGroup
  params: {
    transformationPrincipalId: transformationJob!.outputs.principalId
    storageAccountName: storage.outputs.storageAccountName
    rawContainerName: storage.outputs.rawContainerName
    processedContainerName: storage.outputs.processedContainerName
    curatedContainerName: storage.outputs.curatedContainerName
    quarantineContainerName: storage.outputs.quarantineContainerName
  }
}

output environmentName string = environment
output environmentResourceGroupName string = platformResourceGroup.name
output storageAccountId string = storage.outputs.storageAccountId
output rawContainerName string = storage.outputs.rawContainerName
output processedContainerName string = storage.outputs.processedContainerName
output curatedContainerName string = storage.outputs.curatedContainerName
output quarantineContainerName string = storage.outputs.quarantineContainerName
output dataFactoryId string = dataFactory.outputs.dataFactoryId
output dataFactoryPrincipalId string = dataFactory.outputs.principalId
output containerRegistryId string = registry.outputs.registryId
output containerRegistryLoginServer string = registry.outputs.loginServer
output containerAppsEnvironmentId string = containerAppsEnvironment.outputs.environmentId
output transformationJobId string = deployTransformationJob ? transformationJob!.outputs.jobId : ''
output transformationJobPrincipalId string = deployTransformationJob ? transformationJob!.outputs.principalId : ''
output keyVaultId string = keyVault.outputs.keyVaultId
output logAnalyticsWorkspaceId string = monitoring.outputs.workspaceId
output postgresqlServerId string = postgresql.outputs.serverId
output postgresqlFullyQualifiedDomainName string = postgresql.outputs.fullyQualifiedDomainName
