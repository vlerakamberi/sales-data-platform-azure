param dataFactoryPrincipalId string
param jobName string

resource transformationJob 'Microsoft.App/jobs@2025-07-01' existing = {
  name: jobName
}

var containerAppsJobsOperatorRoleDefinitionId = subscriptionResourceId(
  'Microsoft.Authorization/roleDefinitions',
  'b9a307c4-5aa3-4b52-ba60-2b17c136cd7b'
)

resource adfJobOperator 'Microsoft.Authorization/roleAssignments@2022-04-01' = {
  name: guid(transformationJob.id, dataFactoryPrincipalId, containerAppsJobsOperatorRoleDefinitionId)
  scope: transformationJob
  properties: {
    principalId: dataFactoryPrincipalId
    principalType: 'ServicePrincipal'
    roleDefinitionId: containerAppsJobsOperatorRoleDefinitionId
  }
}

output roleAssignmentId string = adfJobOperator.id
