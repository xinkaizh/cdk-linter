import * as path from 'path';
import {
  CfnOutput,
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
} from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as eventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';

export class JobServiceSampleStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const jobsTable = new dynamodb.Table(this, 'JobsTable', {
      tableName: 'cdk-playground-jobs',
      partitionKey: {
        name: 'job_id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const rawBucket = new s3.Bucket(this, 'RawBucket', {
      autoDeleteObjects: true,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const dlq = new sqs.Queue(this, 'JobsDlq', {
      queueName: 'cdk-playground-jobs-dlq',
      retentionPeriod: Duration.days(14),
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const jobsQueue = new sqs.Queue(this, 'JobsQueue', {
      queueName: 'cdk-playground-jobs-queue',
      visibilityTimeout: Duration.seconds(120),
      deadLetterQueue: {
        queue: dlq,
        maxReceiveCount: 3,
      },
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const lambdaCode = lambda.Code.fromAsset(
      path.join(__dirname, '..', 'lambda'),
      {
        exclude: [
          '__pycache__',
          '*.pyc',
          '.pytest_cache',
          '.venv',
          'venv',
          'node_modules',
        ],
      },
    );

    const apiHandler = new lambda.Function(this, 'ApiHandler', {
      functionName: 'cdk-playground-api-handler',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'api_handler.lambda_handler',
      code: lambdaCode,
      timeout: Duration.seconds(15),
      memorySize: 256,
      logRetention: logs.RetentionDays.ONE_WEEK,
      environment: {
        JOBS_TABLE_NAME: jobsTable.tableName,
        RAW_BUCKET_NAME: rawBucket.bucketName,
        QUEUE_URL: jobsQueue.queueUrl,
      },
    });

    const workerHandler = new lambda.Function(this, 'WorkerHandler', {
      functionName: 'cdk-playground-worker-handler',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'worker_handler.lambda_handler',
      code: lambdaCode,
      timeout: Duration.seconds(30),
      memorySize: 256,
      logRetention: logs.RetentionDays.ONE_WEEK,
      environment: {
        JOBS_TABLE_NAME: jobsTable.tableName,
        RAW_BUCKET_NAME: rawBucket.bucketName,
      },
    });

    jobsTable.grantReadWriteData(apiHandler);
    jobsTable.grantReadWriteData(workerHandler);

    rawBucket.grantReadWrite(apiHandler);
    rawBucket.grantRead(workerHandler);

    jobsQueue.grantSendMessages(apiHandler);

    workerHandler.addEventSource(
      new eventSources.SqsEventSource(jobsQueue, {
        batchSize: 1,
      }),
    );

    const api = new apigateway.RestApi(this, 'JobsApi', {
      restApiName: 'cdk-playground-jobs-api',
      deployOptions: {
        stageName: 'prod',
      },
      defaultCorsPreflightOptions: {
        allowOrigins: apigateway.Cors.ALL_ORIGINS,
        allowMethods: apigateway.Cors.ALL_METHODS,
        allowHeaders: ['Content-Type'],
      },
    });

    const jobs = api.root.addResource('jobs');
    jobs.addMethod('POST', new apigateway.LambdaIntegration(apiHandler));

    const jobById = jobs.addResource('{job_id}');
    jobById.addMethod('GET', new apigateway.LambdaIntegration(apiHandler));

    new CfnOutput(this, 'ApiBaseUrl', {
      value: api.url,
    });

    new CfnOutput(this, 'CreateJobEndpoint', {
      value: `${api.url}jobs`,
    });

    new CfnOutput(this, 'GetJobEndpointTemplate', {
      value: `${api.url}jobs/{job_id}`,
    });

    new CfnOutput(this, 'JobsTableName', {
      value: jobsTable.tableName,
    });

    new CfnOutput(this, 'RawBucketName', {
      value: rawBucket.bucketName,
    });

    new CfnOutput(this, 'JobsQueueName', {
      value: jobsQueue.queueName,
    });

    new CfnOutput(this, 'JobsQueueUrl', {
      value: jobsQueue.queueUrl,
    });
  }
}