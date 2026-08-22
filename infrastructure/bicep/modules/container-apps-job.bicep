param jobName string
param location string
param managedEnvironmentId string
param registryServer string
param registryIdentityId string = 'system'
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

resource job 'Microsoft.App/jobs@2025-07-01' = {
  name: jobName
  location: location
  tags: tags
  identity: registryIdentityId == 'system' ? {
    type: 'SystemAssigned'
  } : {
    type: 'SystemAssigned, UserAssigned'
    userAssignedIdentities: {
      '${registryIdentityId}': {}
    }
  }
  properties: {
    environmentId: managedEnvironmentId
    configuration: {
      registries: [
        {
          identity: registryIdentityId
          server: registryServer
        }
      ]
      identitySettings: registryIdentityId == 'system' ? [] : [
        {
          identity: 'system'
          lifecycle: 'Main'
        }
        {
          identity: registryIdentityId
          lifecycle: 'None'
        }
      ]
      replicaRetryLimit: 1
      replicaTimeout: 1800
      triggerType: 'Manual'
      manualTriggerConfig: {
        parallelism: 1
        replicaCompletionCount: 1
      }
    }
    template: {
      containers: [
        {
          name: 'transformation'
          image: imageName
          env: [
            {
              name: 'SDPA_ENVIRONMENT'
              value: environmentName
            }
            {
              name: 'SDPA_STORAGE_ACCOUNT_URL'
              value: 'https://${storageAccountName}.blob.${environment().suffixes.storage}'
            }
            {
              name: 'SDPA_RAW_CONTAINER'
              value: rawContainerName
            }
            {
              name: 'SDPA_PROCESSED_CONTAINER'
              value: processedContainerName
            }
            {
              name: 'SDPA_CURATED_CONTAINER'
              value: curatedContainerName
            }
            {
              name: 'SDPA_QUARANTINE_CONTAINER'
              value: quarantineContainerName
            }
          ]
          resources: {
            cpu: json(cpu)
            memory: memory
          }
        }
      ]
    }
  }
}

output jobId string = job.id
output jobName string = job.name
output principalId string = job.identity.principalId
