"""S3 bucket inventory collection module."""

import json
import os
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class S3Inventory:
    """Handles S3 bucket discovery and object inventory collection."""
    
    def __init__(
        self,
        profile: Optional[str] = None,
        sample_size: int = 100000,
        verbose: bool = False,
        max_workers: int = 10,
    ) -> None:
        """Initialize the S3 inventory collector.
        
        Args:
            profile: AWS profile to use
            sample_size: Number of objects to sample for large buckets (>100M objects)
            verbose: Enable verbose logging
            max_workers: Maximum number of concurrent workers
        """
        self.profile = profile
        self.sample_size = sample_size
        self.verbose = verbose
        self.max_workers = max_workers
        self.session = self._create_session()
        
    def _create_session(self) -> boto3.Session:
        """Create boto3 session with profile if specified."""
        if self.profile:
            return boto3.Session(profile_name=self.profile)
        return boto3.Session()
    
    def discover_buckets(self) -> List[str]:
        """Discover all S3 buckets in the account.
        
        Returns:
            List of bucket names
        """
        try:
            s3_client = self.session.client('s3')
            response = s3_client.list_buckets()
            buckets = [bucket['Name'] for bucket in response['Buckets']]
            
            if self.verbose:
                print(f"Discovered {len(buckets)} buckets")
                
            return buckets
            
        except (NoCredentialsError, ClientError) as e:
            raise RuntimeError(f"Failed to discover buckets: {e}")
    
    def collect_inventory(self, buckets: List[str]) -> Dict[str, Any]:
        """Collect inventory data for all buckets.
        
        Args:
            buckets: List of bucket names to inventory
            
        Returns:
            Dictionary with bucket inventory data
        """
        inventory_data = {}
        
        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit inventory tasks for all buckets
            future_to_bucket = {
                executor.submit(self._inventory_bucket, bucket): bucket
                for bucket in buckets
            }
            
            # Collect results as they complete
            for future in as_completed(future_to_bucket):
                bucket = future_to_bucket[future]
                try:
                    bucket_data = future.result()
                    inventory_data[bucket] = bucket_data
                    
                    if self.verbose:
                        print(f"Completed inventory for {bucket}: {bucket_data['object_count']} objects")
                        
                except Exception as e:
                    print(f"Error inventorying bucket {bucket}: {e}")
                    # Create a minimal bucket entry with error info
                    inventory_data[bucket] = {
                        "bucket_name": bucket,
                        "error": str(e),
                        "object_count": 0,
                        "total_size": 0,
                        "region": "unknown",
                        "sampled": False,
                        "sample_size": 0,
                        "storage_classes": {},
                        "file_extensions": {},
                        "age_buckets": {"recent": 0, "old": 0},
                        "objects": [],
                        "inventory_date": datetime.now().isoformat(),
                    }
        
        return inventory_data
    
    def _inventory_bucket(self, bucket_name: str) -> Dict[str, Any]:
        """Collect inventory data for a single bucket.
        
        Args:
            bucket_name: Name of the bucket to inventory
            
        Returns:
            Dictionary with bucket inventory data
        """
        try:
            s3_client = self.session.client('s3')
            
            # Get bucket location
            try:
                location_response = s3_client.get_bucket_location(Bucket=bucket_name)
                region = location_response.get('LocationConstraint') or 'us-east-1'
            except ClientError:
                region = 'us-east-1'
            
            # Create regional client
            regional_client = self.session.client('s3', region_name=region)
            
            objects = []
            object_count = 0
            total_size = 0
            storage_classes = {}
            file_extensions = {}
            age_buckets = {
                "recent": 0,  # ≤ 30 days
                "old": 0,     # > 30 days
            }
            
            thirty_days_ago = datetime.utcnow().replace(tzinfo=timezone.utc) - timedelta(days=30)
            
            # Use AWS CLI for better performance with large buckets
            paginator = regional_client.get_paginator('list_objects_v2')
            page_iterator = paginator.paginate(
                Bucket=bucket_name,
                PaginationConfig={'PageSize': 1000}
            )
            
            for page in page_iterator:
                if 'Contents' not in page:
                    continue
                    
                for obj in page['Contents']:
                    object_count += 1
                    total_size += obj['Size']
                    
                    # Track storage class
                    storage_class = obj.get('StorageClass', 'STANDARD')
                    storage_classes[storage_class] = storage_classes.get(storage_class, 0) + 1
                    
                    # Track file extension
                    key = obj['Key']
                    extension = self._get_file_extension(key)
                    if extension not in file_extensions:
                        file_extensions[extension] = {"count": 0, "size": 0}
                    file_extensions[extension]["count"] += 1
                    file_extensions[extension]["size"] += obj['Size']
                    
                    # Track age - ensure both datetimes are timezone-aware
                    last_modified = obj['LastModified']
                    
                    # Convert both to UTC for comparison
                    if last_modified.tzinfo is None:
                        # If last_modified is naive, assume it's UTC
                        last_modified_utc = last_modified.replace(tzinfo=timezone.utc)
                    else:
                        # If it's already timezone-aware, convert to UTC
                        last_modified_utc = last_modified.astimezone(timezone.utc)
                    
                    try:
                        if last_modified_utc > thirty_days_ago:
                            age_buckets["recent"] += 1
                        else:
                            age_buckets["old"] += 1
                    except Exception as e:
                        # If there's still a timezone issue, skip age tracking for this object
                        if self.verbose:
                            print(f"Warning: Could not determine age for object {key}: {e}")
                        # Default to old if we can't determine
                        age_buckets["old"] += 1
                    
                    # Store object data (with sampling for large buckets)
                    if object_count <= self.sample_size or object_count <= 100000000:
                        objects.append({
                            "key": key,
                            "size": obj['Size'],
                            "last_modified": last_modified.isoformat(),
                            "storage_class": storage_class,
                            "etag": obj.get('ETag', ''),
                        })
                    
                    # Apply sampling for very large buckets
                    if object_count > 100000000 and len(objects) >= self.sample_size:
                        break
                
                # Break if we've sampled enough
                if object_count > 100000000 and len(objects) >= self.sample_size:
                    break
            
            # Convert file extensions to sorted list
            sorted_extensions = sorted(
                file_extensions.items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )
            
            return {
                "bucket_name": bucket_name,
                "region": region,
                "object_count": object_count,
                "total_size": total_size,
                "sampled": object_count > 100000000 and len(objects) < object_count,
                "sample_size": len(objects),
                "storage_classes": storage_classes,
                "file_extensions": dict(sorted_extensions),
                "age_buckets": age_buckets,
                "objects": objects,
                "inventory_date": datetime.now().isoformat(),
            }
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            if error_code == 'AccessDenied':
                return {
                    "bucket_name": bucket_name,
                    "error": "Access denied",
                    "object_count": 0,
                    "total_size": 0,
                    "objects": [],
                }
            else:
                raise
    
    def _get_file_extension(self, key: str) -> str:
        """Extract file extension from S3 key.
        
        Args:
            key: S3 object key
            
        Returns:
            File extension (lowercase, without dot)
        """
        # Handle directory-like keys
        if key.endswith('/'):
            return "directory"
        
        # Extract extension
        path = Path(key)
        extension = path.suffix.lower()
        
        if extension:
            return extension[1:]  # Remove the dot
        else:
            return "no-extension"
    
    def write_inventory(self, inventory_data: Dict[str, Any], output_file: str) -> None:
        """Write inventory data to JSONL file.
        
        Args:
            inventory_data: Inventory data dictionary
            output_file: Output file path
        """
        with open(output_file, 'w') as f:
            for bucket_name, bucket_data in inventory_data.items():
                f.write(json.dumps(bucket_data) + '\n')
    
    def load_inventory(self, inventory_file: str) -> Dict[str, Any]:
        """Load inventory data from JSONL file.
        
        Args:
            inventory_file: Input file path
            
        Returns:
            Dictionary with bucket inventory data
        """
        inventory_data = {}
        
        with open(inventory_file, 'r') as f:
            for line in f:
                bucket_data = json.loads(line.strip())
                bucket_name = bucket_data.get('bucket_name', 'unknown')
                inventory_data[bucket_name] = bucket_data
        
        return inventory_data 