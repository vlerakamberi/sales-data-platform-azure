targetScope = 'resourceGroup'

param dataFactoryName string
param jobName string
param pipelineName string
param triggerName string

var pipelineArtifact = loadJsonContent('../../orchestration/adf/pipelines/northstar-sales-orchestration.json')
var triggerArtifact = loadJsonContent('../../orchestration/adf/triggers/northstar-sales-schedule.json')
var deployedTriggerProperties = union(triggerArtifact.properties, {
  pipelines: [
    union(triggerArtifact.properties.pipelines[0], {
      parameters: union(triggerArtifact.properties.pipelines[0].parameters, {
        subscriptionId: subscription().subscriptionId
      })
    })
  ]
})

resource dataFactory 'Microsoft.DataFactory/factories@2018-06-01' existing = {
  name: dataFactoryName
}

module orchestration 'modules/adf-orchestration.bicep' = {
  name: 'unit8-adf-orchestration'
  params: {
    dataFactoryName: dataFactory.name
    pipelineName: pipelineName
    pipelineProperties: pipelineArtifact.properties
    triggerName: triggerName
    triggerProperties: deployedTriggerProperties
  }
}

module orchestrationRbac 'modules/adf-orchestration-rbac.bicep' = {
  name: 'unit8-adf-orchestration-rbac'
  params: {
    dataFactoryPrincipalId: dataFactory.identity.principalId
    jobName: jobName
  }
}

output pipelineId string = orchestration.outputs.pipelineId
output triggerId string = orchestration.outputs.triggerId
output roleAssignmentId string = orchestrationRbac.outputs.roleAssignmentId
