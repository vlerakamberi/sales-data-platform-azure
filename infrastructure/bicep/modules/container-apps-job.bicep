param jobName string
param location string
param managedEnvironmentId string
param registryServer string
param imageName string
param environmentName string
param cpu string
param memory string
param tags object

resource job 'Microsoft.App/jobs@2025-07-01' = {
  name: jobName
  location: location
  tags: tags
  identity: {
    type: 'SystemAssigned'
  }
  properties: {
    environmentId: managedEnvironmentId
    configuration: {
      registries: [
        {
          identity: 'system'
          server: registryServer
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
