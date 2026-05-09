import {
    Duration,
    Stack,
    StackProps
} from 'aws-cdk-lib';
import * as apigateway from 'aws-cdk-lib/aws-apigateway';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as eventSources from 'aws-cdk-lib/aws-lambda-event-sources';
import * as logs from 'aws-cdk-lib/aws-logs';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';
import * as path from 'path';

export interface LambdaStackProps extends StackProps {
  jobsTable: dynamodb.ITable;
  rawBucket: s3.IBucket;
  jobsQueue: sqs.IQueue;
}

export class LambdaStack extends Stack {
  public readonly apiHandler: lambda.Function;
  public readonly workerHandler: lambda.Function;
  
  constructor(scope: Construct, id: string, props: LambdaStackProps) {
    super(scope, id, props);

    const { jobsTable, rawBucket, jobsQueue } = props;

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

    this.apiHandler = new lambda.Function(this, 'ApiHandler', {
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

    this.workerHandler = new lambda.Function(this, 'WorkerHandler', {
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

    jobsTable.grantReadWriteData(this.apiHandler);
    jobsTable.grantReadWriteData(this.workerHandler);

    rawBucket.grantReadWrite(this.apiHandler);
    rawBucket.grantRead(this.workerHandler);

    jobsQueue.grantSendMessages(this.apiHandler);

    this.workerHandler.addEventSource(
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
    jobs.addMethod('POST', new apigateway.LambdaIntegration(this.apiHandler));

    const jobById = jobs.addResource('{job_id}');
    jobById.addMethod('GET', new apigateway.LambdaIntegration(this.apiHandler));
  }
}