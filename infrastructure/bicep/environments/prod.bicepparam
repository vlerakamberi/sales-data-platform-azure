using '../main.bicep'

param environment = 'production'
param location = 'northeurope'
param namingPrefix = 'nsrsdp'
param governanceTags = {
  costOwner: 'data-engineering'
  portfolio: 'northstar-retail'
  project: 'cloud-data-platform-foundation'
}
param storageSku = 'Standard_GRS'
param storageDeleteRetentionDays = 30
param rawCoolAfterDays = 30
param derivedDataDeleteAfterDays = 90
param containerRegistrySku = 'Standard'
param logRetentionDays = 90
param jobCpu = '1.0'
param jobMemory = '2Gi'
param transformationImage = 'nsrsdp-prod-transformation:unit3-not-implemented'
param deployTransformationJob = false
param postgresqlSkuName = 'Standard_D2ds_v5'
param postgresqlSkuTier = 'GeneralPurpose'
param postgresqlStorageSizeGb = 128
param postgresqlBackupRetentionDays = 35
