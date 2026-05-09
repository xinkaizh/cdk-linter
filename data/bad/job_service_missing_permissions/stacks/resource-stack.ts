import {
  Duration,
  RemovalPolicy,
  Stack,
  StackProps
} from 'aws-cdk-lib';
import * as dynamodb from 'aws-cdk-lib/aws-dynamodb';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sqs from 'aws-cdk-lib/aws-sqs';
import { Construct } from 'constructs';

export class ResourceStack extends Stack {
  public readonly jobsTable: dynamodb.Table;
  public readonly rawBucket: s3.Bucket;
  public readonly jobsQueue: sqs.Queue;
  
  constructor(scope: Construct, id: string, props?: StackProps) {
    super(scope, id, props);

    this.jobsTable = new dynamodb.Table(this, 'JobsTable', {
      tableName: 'cdk-playground-jobs',
      partitionKey: {
        name: 'job_id',
        type: dynamodb.AttributeType.STRING,
      },
      billingMode: dynamodb.BillingMode.PAY_PER_REQUEST,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.rawBucket = new s3.Bucket(this, 'RawBucket', {
      autoDeleteObjects: true,
      removalPolicy: RemovalPolicy.DESTROY,
    });

    const dlq = new sqs.Queue(this, 'JobsDlq', {
      queueName: 'cdk-playground-jobs-dlq',
      retentionPeriod: Duration.days(14),
      removalPolicy: RemovalPolicy.DESTROY,
    });

    this.jobsQueue = new sqs.Queue(this, 'JobsQueue', {
      queueName: 'cdk-playground-jobs-queue',
      visibilityTimeout: Duration.seconds(120),
      deadLetterQueue: {
        queue: dlq,
        maxReceiveCount: 3,
      },
      removalPolicy: RemovalPolicy.DESTROY,
    });
  }
}