"""Utility functions for S3-Insight."""

import subprocess
from typing import Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


def get_aws_account_id(profile: Optional[str] = None) -> str:
    """Get AWS account ID using STS.
    
    Args:
        profile: AWS profile to use
        
    Returns:
        AWS account ID
        
    Raises:
        RuntimeError: If unable to get account ID
    """
    try:
        if profile:
            session = boto3.Session(profile_name=profile)
        else:
            session = boto3.Session()
        
        sts_client = session.client('sts')
        response = sts_client.get_caller_identity()
        return response['Account']
        
    except (NoCredentialsError, ClientError) as e:
        raise RuntimeError(f"Failed to get AWS account ID: {e}")


def format_bytes(bytes_value: int) -> str:
    """Format bytes into human-readable string.
    
    Args:
        bytes_value: Number of bytes
        
    Returns:
        Formatted string (e.g., "1.5 GB")
    """
    if bytes_value == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB", "PB"]
    import math
    i = int(math.floor(math.log(bytes_value, 1024)))
    p = math.pow(1024, i)
    s = round(bytes_value / p, 2)
    return f"{s} {size_names[i]}"


def format_number(number: int) -> str:
    """Format large numbers with commas.
    
    Args:
        number: Number to format
        
    Returns:
        Formatted string with commas
    """
    return f"{number:,}"


def run_aws_cli_command(command: list, profile: Optional[str] = None) -> str:
    """Run AWS CLI command and return output.
    
    Args:
        command: List of command arguments
        profile: AWS profile to use
        
    Returns:
        Command output as string
        
    Raises:
        RuntimeError: If command fails
    """
    try:
        if profile:
            command = ["aws", "--profile", profile] + command[1:]
        
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
        
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"AWS CLI command failed: {e.stderr}")


def validate_aws_credentials(profile: Optional[str] = None) -> bool:
    """Validate AWS credentials are configured and working.
    
    Args:
        profile: AWS profile to use
        
    Returns:
        True if credentials are valid, False otherwise
    """
    try:
        get_aws_account_id(profile)
        return True
    except RuntimeError:
        return False


def get_s3_bucket_region(bucket_name: str, profile: Optional[str] = None) -> str:
    """Get the region of an S3 bucket.
    
    Args:
        bucket_name: Name of the S3 bucket
        profile: AWS profile to use
        
    Returns:
        Bucket region
        
    Raises:
        RuntimeError: If unable to get bucket region
    """
    try:
        if profile:
            session = boto3.Session(profile_name=profile)
        else:
            session = boto3.Session()
        
        s3_client = session.client('s3')
        response = s3_client.get_bucket_location(Bucket=bucket_name)
        region = response.get('LocationConstraint')
        
        # us-east-1 returns None for LocationConstraint
        return region or 'us-east-1'
        
    except ClientError as e:
        raise RuntimeError(f"Failed to get bucket region for {bucket_name}: {e}")


def estimate_cost_gb_per_month(storage_class: str, region: str = "us-east-1") -> float:
    """Estimate monthly cost per GB for S3 storage class.
    
    Args:
        storage_class: S3 storage class
        region: AWS region
        
    Returns:
        Estimated cost per GB per month in USD
    """
    # Approximate costs per GB per month (us-east-1, as of 2024)
    # These are rough estimates and may vary
    costs = {
        "STANDARD": 0.023,
        "STANDARD_IA": 0.0125,
        "ONEZONE_IA": 0.01,
        "INTELLIGENT_TIERING": 0.023,
        "GLACIER": 0.004,
        "DEEP_ARCHIVE": 0.00099,
        "GLACIER_IR": 0.004,
    }
    
    return costs.get(storage_class, 0.023)  # Default to STANDARD cost


def calculate_estimated_monthly_cost(
    total_size_gb: float,
    storage_class_breakdown: dict
) -> float:
    """Calculate estimated monthly S3 storage cost.
    
    Args:
        total_size_gb: Total size in GB
        storage_class_breakdown: Dictionary with storage class percentages
        
    Returns:
        Estimated monthly cost in USD
    """
    total_cost = 0.0
    
    for storage_class, data in storage_class_breakdown.items():
        if isinstance(data, dict) and 'percentage' in data:
            # Calculate size for this storage class
            class_size_gb = (data['percentage'] / 100) * total_size_gb
            cost_per_gb = estimate_cost_gb_per_month(storage_class)
            total_cost += class_size_gb * cost_per_gb
        elif isinstance(data, int):
            # Simple count-based breakdown
            percentage = data / sum(storage_class_breakdown.values()) * 100
            class_size_gb = (percentage / 100) * total_size_gb
            cost_per_gb = estimate_cost_gb_per_month(storage_class)
            total_cost += class_size_gb * cost_per_gb
    
    return total_cost 