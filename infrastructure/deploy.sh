#!/bin/bash
set -e

AWS_REGION="us-east-1"
ECR_REPO="risk-monitor"
ECS_CLUSTER="risk-cluster"
ECS_SERVICE="risk-service"

# 1. Build and tag
docker build -f Dockerfile.prod -t $ECR_REPO:latest .

# 2. ECR Login & Push
aws ecr get-login-password --region $AWS_REGION | docker login --username AWS --password-stdin $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com
docker tag $ECR_REPO:latest $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest
docker push $(aws sts get-caller-identity --query Account --output text).dkr.ecr.$AWS_REGION.amazonaws.com/$ECR_REPO:latest

# 3. Force ECS to redeploy
aws ecs update-service --cluster $ECS_CLUSTER --service $ECS_SERVICE --force-new-deployment --region $AWS_REGION

echo "Deployment complete!"
