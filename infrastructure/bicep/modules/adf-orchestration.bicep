param dataFactoryName string
param pipelineName string
param pipelineProperties object
param triggerName string
param triggerProperties object

resource dataFactory 'Microsoft.DataFactory/factories@2018-06-01' existing = {
  name: dataFactoryName
}

resource pipeline 'Microsoft.DataFactory/factories/pipelines@2018-06-01' = {
  parent: dataFactory
  name: pipelineName
  properties: pipelineProperties
}

resource trigger 'Microsoft.DataFactory/factories/triggers@2018-06-01' = {
  parent: dataFactory
  name: triggerName
  properties: triggerProperties
}

output pipelineId string = pipeline.id
output triggerId string = trigger.id
