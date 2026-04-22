#!/usr/bin/env node
import 'source-map-support/register';
import * as cdk from 'aws-cdk-lib';
import { JobServiceSampleStack } from './stacks/job-service-sample-stack';

const app = new cdk.App();

new JobServiceSampleStack(app, 'JobServiceSampleStack', {
  env: {
    account: process.env.CDK_DEFAULT_ACCOUNT,
    region: process.env.CDK_DEFAULT_REGION,
  },
});