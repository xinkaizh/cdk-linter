#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { JobServiceWrongResourceStack } from '../lib/job-service-wrong-resource-stack';

const app = new cdk.App();

// Bad fixture: IAM grant targets OtherTable when the spec asks about JobsTable
new JobServiceWrongResourceStack(app, 'JobServiceWrongResourceStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  }
});