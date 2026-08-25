from aws_cdk import Stack, aws_ecs as ecs, aws_ec2 as ec2
from constructs import Construct

class RiskMonitorStack(Stack):
    def __init__(self, scope: Construct, id: str, **kwargs):
        super().__init__(scope, id, **kwargs)
        
        vpc = ec2.Vpc.from_lookup(self, "VPC", is_default=True)
        cluster = ecs.Cluster(self, "RiskCluster", vpc=vpc)
        
        # Fargate task definition
        task_def = ecs.FargateTaskDefinition(self, "RiskTask", memory_limit_mib=512, cpu=256)
        container = task_def.add_container("RiskContainer", 
            image=ecs.ContainerImage.from_registry("your-ecr-repo:latest"),
            environment={"PINECONE_API_KEY": "value"} # Use Secrets Manager for real secrets
        )
        
        ecs.FargateService(self, "RiskService", cluster=cluster, task_definition=task_def)
