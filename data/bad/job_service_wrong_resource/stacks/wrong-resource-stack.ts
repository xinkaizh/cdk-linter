import * as path from 'path';
import {
  Duration,
  RemovalPolicy,
  Stack,
  StackProps,
} from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as lambda from 'aws-cdk-lib/aws-lambda';
import * as logs from 'aws-cdk-lib/aws-logs';
import { Construct } from 'constructs';

export class JobServiceWrongResourceStack extends Stack {
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    const jobsTable = new dynamodb.Table(this, 'JobsTable', {
      tableName: 'cdk-playground-wrong-res-jobs',
      partitionKey: {
        name: 'job_id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const otherTable = new dynamodb.Table(this, 'OtherTable', {
      tableName: 'cdk-playground-wrong-res-other',
      partitionKey: {
        name: 'id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
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
      functionName: 'cdk-playground-wrong-res-api',
      runtime: lambda.Runtime.PYTHON_3_12,
      handler: 'api_handler.lambda_handler',
      code: lambdaCode,
      timeout: Duration.seconds(15),
      memorySize: 256,
      logRetention: logs.RetentionDays.ONE_WEEK,
      environment: {
        JOBS_TABLE_NAME: jobsTable.tableName,
      },
    });

    otherTable.grantReadWriteData(apiHandler);
  }
}