using '../main.bicep'

param environment = 'development'
param location = 'francecentral'
param namingPrefix = 'nsrsdp'
param governanceTags = {
  costOwner: 'data-engineering'
  portfolio: 'northstar-retail'
  project: 'cloud-data-platform-foundation'
}
param storageSku = 'Standard_LRS'
param storageDeleteRetentionDays = 7
param rawCoolAfterDays = 30
param derivedDataDeleteAfterDays = 30
param containerRegistrySku = 'Basic'
param logRetentionDays = 30
param jobCpu = '0.5'
param jobMemory = '1Gi'
param transformationImage = 'nsrsdp-dev-transformation:unit3-not-implemented'
param deployTransformationJob = false
param postgresqlSkuName = 'Standard_B1ms'
param postgresqlSkuTier = 'Burstable'
param postgresqlStorageSizeGb = 32
param postgresqlBackupRetentionDays = 7
