import * as cdk from 'aws-cdk-lib';
import { Vpc, Instance, InstanceType, MachineImage, SecurityGroup, Peer, Port } from 'aws-cdk-lib/aws-ec2';

export class Ec2Stack extends cdk.Stack {
  constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
    super(scope, id, props);

    // Create a VPC
    const vpc = new Vpc(this, 'MyVpc', {
      maxAzs: 2, // Default is all AZs in region
    });

    // Create a security group
    const securityGroup = new SecurityGroup(this, 'MySecurityGroup', {
      vpc,
      description: 'Allow SSH access',
      allowAllOutbound: true,
    });

    // Allow SSH access from anywhere (for demo purposes)
    securityGroup.addIngressRule(Peer.anyIpv4(), Port.tcp(22), 'Allow SSH access');

    // Create an EC2 instance
    const instance = new Instance(this, 'MyInstance', {
      vpc,
      instanceType: new InstanceType('t2.micro'),
      machineImage: MachineImage.latestAmazonLinux2(),
      securityGroup,
      keyName: 'my-key-pair', // You'll need to create this key pair in AWS
    });

    // Output the instance ID and public IP
    new cdk.CfnOutput(this, 'InstanceId', {
      value: instance.instanceId,
      description: 'EC2 Instance ID',
    });

    new cdk.CfnOutput(this, 'InstancePublicIp', {
      value: instance.instancePublicIp,
      description: 'EC2 Instance Public IP',
    });
  }
}