#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { JobServicePartialPermissionStack } from '../lib/job-service-partial-permission-stack';

const app = new cdk.App();

// Bad fixture: partial IAM permissions on the job-service stack
new JobServicePartialPermissionStack(app, 'JobServicePartialPermissionStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  }
});