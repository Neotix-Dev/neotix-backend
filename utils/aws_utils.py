import boto3
import os
import time
from botocore.exceptions import ClientError
from typing import Dict, Tuple, Optional
from botocore.exceptions import WaiterError

class AWSManager:
    # AWS GPU instance type mapping
    GPU_INSTANCE_MAPPING = {
        'T4': 'g4dn.xlarge',     # 1x T4 GPU
        'A100': 'p4d.24xlarge',  # 8x A100 GPUs
        'A10G': 'g5.2xlarge',    # 1x A10G GPU
        'V100': 'p3.2xlarge',    # 1x V100 GPU
        'K80': 'p2.xlarge',      # 1x K80 GPU
    }

    def __init__(self):
        """Initialize AWS manager with credentials from environment."""
        self.ec2_client = boto3.client(
            "ec2",
            region_name='us-east-1',  # Explicitly set region
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )
        self.ec2_resource = boto3.resource(
            "ec2",
            region_name='us-east-1',  # Explicitly set region
            aws_access_key_id=os.getenv('AWS_ACCESS_KEY_ID'),
            aws_secret_access_key=os.getenv('AWS_SECRET_ACCESS_KEY')
        )

    def ensure_security_group_exists(self) -> str:
        """
        Create a new security group with SSH access.
        Returns the security group name.
        """
        group_name = f"neotix-gpu-{int(time.time())}"  # Unique name
        try:
            # Create a new security group
            response = self.ec2_client.create_security_group(
                GroupName=group_name,
                Description='Security group for Neotix GPU instances with SSH access'
            )
            security_group_id = response['GroupId']
            
            # Add SSH access
            self.ec2_client.authorize_security_group_ingress(
                GroupId=security_group_id,
                IpPermissions=[
                    {
                        'IpProtocol': 'tcp',
                        'FromPort': 22,
                        'ToPort': 22,
                        'IpRanges': [{'CidrIp': '0.0.0.0/0'}]
                    }
                ]
            )
            
            print(f"Created security group: {group_name}")
            return group_name
            
        except Exception as e:
            print(f"Error creating security group: {str(e)}")
            raise

    def create_key_pair(self, key_name: str) -> Dict:
        """Create an EC2 key pair and return the private key."""
        try:
            key_pair = self.ec2_client.create_key_pair(KeyName=key_name)
            return {
                'KeyName': key_pair['KeyName'],
                'KeyMaterial': key_pair['KeyMaterial']
            }
        except ClientError as e:
            if e.response['Error']['Code'] == 'InvalidKeyPair.Duplicate':
                # Delete existing key pair and try again
                self.ec2_client.delete_key_pair(KeyName=key_name)
                return self.create_key_pair(key_name)
            raise e

    def delete_key_pair(self, key_name: str) -> None:
        """Delete an EC2 key pair."""
        try:
            self.ec2_client.delete_key_pair(KeyName=key_name)
        except Exception as e:
            print(f"Error deleting key pair: {str(e)}")

    def get_instance_type(self, gpu_config: Dict) -> Optional[str]:
        """
        Determine the appropriate AWS instance type based on GPU configuration.
        """
        print("Determining instance type for GPU config:", gpu_config)
        gpu_name = gpu_config.get('gpu_name', '').replace('NVIDIA ', '').strip()  # Remove 'NVIDIA ' prefix and whitespace
        gpu_count = gpu_config.get('gpu_count', 1)
        
        print(f"Cleaned GPU name: '{gpu_name}'")
        # Direct mapping if available
        for gpu_type, instance_type in self.GPU_INSTANCE_MAPPING.items():
            print(f"Checking if '{gpu_type.lower()}' matches '{gpu_name.lower()}'")
            if gpu_type.lower() == gpu_name.lower():  # Changed to exact match
                print(f"Found matching GPU type: {gpu_type} -> {instance_type}")
                # For multiple GPUs, use larger instance types
                if gpu_count > 1:
                    if 'xlarge' in instance_type:
                        base = instance_type.split('.')[0]
                        size = int(instance_type.split('.')[1].replace('xlarge', ''))
                        return f"{base}.{size * gpu_count}xlarge"
                return instance_type
        
        # Fallback to default based on memory requirements
        gpu_memory = gpu_config.get('gpu_memory', 0)
        print(f"No direct match found, using memory-based fallback. GPU Memory: {gpu_memory}GB")
        if gpu_memory >= 80:  # A100 level
            return 'p4d.24xlarge'
        elif gpu_memory >= 32:  # V100 level
            return 'p3.2xlarge'
        elif gpu_memory >= 16:  # T4/A10G level
            return 'g4dn.xlarge'
        else:
            return 'g4dn.xlarge'  # Smallest GPU instance

    def get_running_instances(self) -> list:
        """Get all running instances."""
        instances = self.ec2_resource.instances.filter(
            Filters=[{
                'Name': 'instance-state-name',
                'Values': ['pending', 'running']
            }]
        )
        return list(instances)

    def get_instance_by_id(self, instance_id: str):
        """Get instance by ID."""
        instances = list(self.ec2_resource.instances.filter(
            Filters=[
                {'Name': 'instance-id', 'Values': [instance_id]},
                {'Name': 'instance-state-name', 'Values': ['pending', 'running']}
            ]
        ))
        return instances[0] if instances else None

    def launch_gpu_instance(
        self,
        gpu_config: Dict,
        key_name: str,
        ami_id: str = None,
        subnet_id: str = None
    ) -> Tuple[str, Dict]:
        """
        Launch an EC2 Spot instance with the specified GPU configuration.
        Args:
            gpu_config: Dictionary containing GPU configuration
            key_name: Name of the SSH key pair
            ami_id: Optional AMI ID
            subnet_id: Optional subnet ID
        Returns:
            Tuple of (instance_id, instance_details)
        """
        if not ami_id:
            ami_id = 'ami-0c7217cdde317cfec'  # Ubuntu 22.04 LTS with NVIDIA drivers

        instance_type = self.get_instance_type(gpu_config)
        if not instance_type:
            raise ValueError(f"Could not determine instance type for GPU configuration: {gpu_config}")

        try:
            # Create a new security group with SSH access
            security_group = self.ensure_security_group_exists()
            
            # Request Spot Instance
            print(f"Requesting spot instance of type {instance_type}")
            try:
                spot_request = self.ec2_client.request_spot_instances(
                    InstanceCount=1,
                    LaunchSpecification={
                        'ImageId': ami_id,
                        'InstanceType': instance_type,
                        'KeyName': key_name,
                        'SecurityGroups': [security_group],
                        'Placement': {
                            'AvailabilityZone': 'us-east-1a'
                        }
                    },
                    Type='one-time'
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'MaxSpotInstanceCountExceeded':
                    error_msg = (
                        "You have reached your spot instance limit. Please:\n"
                        "1. Check AWS Console -> EC2 -> Limits -> Running Spot Instances\n"
                        "2. Request a limit increase or terminate existing instances\n"
                        "3. Try again in a few minutes"
                    )
                    raise Exception(error_msg)
                raise e

            # Get the Spot Instance request ID
            spot_request_id = spot_request['SpotInstanceRequests'][0]['SpotInstanceRequestId']
            print(f"Spot request ID: {spot_request_id}")

            # Wait for the spot request to be fulfilled
            print("Waiting for spot request to be fulfilled...")
            waiter = self.ec2_client.get_waiter('spot_instance_request_fulfilled')
            try:
                waiter.wait(
                    SpotInstanceRequestIds=[spot_request_id],
                    WaiterConfig={
                        'Delay': 5,
                        'MaxAttempts': 48  # Wait up to 4 minutes
                    }
                )
            except WaiterError:
                # Check spot request status
                spot_request_info = self.ec2_client.describe_spot_instance_requests(
                    SpotInstanceRequestIds=[spot_request_id]
                )
                status = spot_request_info['SpotInstanceRequests'][0].get('Status', {})
                status_code = status.get('Code', 'unknown')
                status_message = status.get('Message', 'No message available')
                
                # Cancel the spot request since it failed
                self.ec2_client.cancel_spot_instance_requests(
                    SpotInstanceRequestIds=[spot_request_id]
                )
                
                if status_code == 'capacity-not-available':
                    error_msg = (
                        "No spot capacity available. You can:\n"
                        "1. Try a different availability zone\n"
                        "2. Wait a few minutes and try again\n"
                        "3. Request an on-demand instance instead"
                    )
                    raise Exception(error_msg)
                raise Exception(f"Spot request failed: {status_message}")

            # Get the instance ID
            spot_request_info = self.ec2_client.describe_spot_instance_requests(
                SpotInstanceRequestIds=[spot_request_id]
            )
            instance_id = spot_request_info['SpotInstanceRequests'][0]['InstanceId']
            print(f"Spot instance ID: {instance_id}")

            # Wait for the instance to be running with increased timeout
            print("Waiting for instance to be running...")
            instance = self.ec2_resource.Instance(instance_id)
            instance.wait_until_running(
                Filters=[{
                    'Name': 'instance-state-name',
                    'Values': ['running']
                }],
                WaiterConfig={
                    'Delay': 5,
                    'MaxAttempts': 48  # Wait up to 4 minutes
                }
            )
            instance.load()  # Reload instance attributes

            return instance_id, {
                'instance_id': instance_id,
                'instance_type': instance_type,
                'instance_ip': instance.public_ip_address,
                'instance_dns': instance.public_dns_name,
                'gpu_configuration': gpu_config
            }

        except Exception as e:
            print(f"Error launching EC2 instance: {str(e)}")
            # Clean up key pair if creation fails
            self.delete_key_pair(key_name)
            raise

    def terminate_instance(self, instance_id: str) -> None:
        """Terminate an EC2 instance."""
        try:
            instance = self.ec2_resource.Instance(instance_id)
            instance.terminate()
            instance.wait_until_terminated()
        except ClientError as e:
            raise Exception(f"Failed to terminate EC2 instance: {str(e)}")

    def terminate_all_instances(self) -> None:
        """Terminate all running instances."""
        try:
            # Get all instances
            instances = self.ec2_resource.instances.filter(
                Filters=[
                    {'Name': 'instance-state-name', 'Values': ['pending', 'running']}
                ]
            )
            
            # Terminate instances
            for instance in instances:
                print(f"Terminating instance: {instance.id}")
                instance.terminate()
                
            # Cancel any spot requests
            spot_requests = self.ec2_client.describe_spot_instance_requests(
                Filters=[
                    {'Name': 'state', 'Values': ['open', 'active']}
                ]
            )
            
            for request in spot_requests['SpotInstanceRequests']:
                request_id = request['SpotInstanceRequestId']
                print(f"Canceling spot request: {request_id}")
                self.ec2_client.cancel_spot_instance_requests(
                    SpotInstanceRequestIds=[request_id]
                )
                
        except Exception as e:
            print(f"Error terminating instances: {str(e)}")
