#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { FullStack } from '../lib/full-stack';
import { ResourceStack } from '../lib/resource-stack';
import { LambdaStack } from '../lib/lambda-stack';
import { MissingPermissionStack } from '../lib/missing-permission-stack';

const app = new cdk.App();

// full stack containing all resources and lambda functions
new FullStack(app, 'FullStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  }
});

// full stack (but missing IAM permissions)
new MissingPermissionStack(app, 'MissingPermissionStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  }
});

// separate stacks for resources and lambda functions
const resourceStack = new ResourceStack(app, 'ResourceStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  }
});

const lambdaStack =new LambdaStack(app, 'LambdaStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  },
  jobsTable: resourceStack.jobsTable,
  rawBucket: resourceStack.rawBucket,
  jobsQueue: resourceStack.jobsQueue
});