#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as ecr from 'aws-cdk-lib/aws-ecr';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as kms from 'aws-cdk-lib/aws-kms';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as rds from 'aws-cdk-lib/aws-rds';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';

class BadTsAllRulesStack extends cdk.Stack {
  constructor(scope: Construct, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    new s3.Bucket(this, 'InvalidBucketName', {
      bucketName: 'Invalid_Bucket',
    });

    lambda.Code.fromAsset('lambda/api_handler.py');

    new iam.Role(this, 'InvalidRoleName', {
      roleName: 'Bad*Role',
      assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
    });

    new iam.Role(
      this,
      'RoleConstructIdThatIsIntentionallyLongerThanSixtyFourCharactersForFixture',
      {
        assumedBy: new iam.ServicePrincipal('lambda.amazonaws.com'),
      },
    );

    new rds.DatabaseCluster(this, 'InvalidClusterIdentifier', {
      clusterIdentifier: 'bad_cluster',
    });

    new lambda.Function(this, 'InvalidFunctionName', {
      functionName: 'bad function name',
      code: lambda.Code.fromAsset('lambda/'),
      handler: 'index.handler',
      runtime: lambda.Runtime.NODEJS_20_X,
    });

    new sqs.Queue(this, 'InvalidQueueName', {
      queueName: 'orders',
      fifo: true,
    });

    new sns.Topic(this, 'InvalidTopicName', {
      topicName: 'bad.topic',
    });

    new dynamodb.Table(this, 'InvalidTableName', {
      tableName: 'ab',
      partitionKey: {
        name: 'id',
        type: dynamodb.AttributeType.STRING,
      },
    });

    new logs.LogGroup(this, 'InvalidLogGroupName', {
      logGroupName: 'bad log group',
    });

    new kms.Alias(this, 'InvalidAliasName', {
      aliasName: 'alias/aws/service',
    });

    new ecr.Repository(this, 'InvalidRepositoryName', {
      repositoryName: 'Team/Service',
    });

    new lambda.Function(this, 'TimeoutTooLong', {
      functionName: 'timeout-too-long',
      code: lambda.Code.fromAsset('lambda/'),
      handler: 'index.handler',
      runtime: lambda.Runtime.NODEJS_20_X,
      timeout: cdk.Duration.minutes(20),
    });

    new sqs.Queue(this, 'RetentionTooShort', {
      queueName: 'retention-too-short',
      retentionPeriod: cdk.Duration.seconds(30),
    });

    new sqs.Queue(this, 'ReceiveWaitTooLong', {
      queueName: 'receive-wait-too-long',
      receiveMessageWaitTime: cdk.Duration.seconds(45),
    });
  }
}

const app = new cdk.App();
new BadTsAllRulesStack(app, 'BadTsAllRulesStack');
