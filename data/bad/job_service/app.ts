#!/usr/bin/env node
import * as cdk from 'aws-cdk-lib';
import { MissingPermissionStack } from '../lib/missing-permission-stack';

const app = new cdk.App();

// full stack (but missing IAM permissions)
new MissingPermissionStack(app, 'MissingPermissionStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION
  }
});
