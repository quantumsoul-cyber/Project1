"""Tests for the inventory module."""

import json
import tempfile
from unittest.mock import Mock, patch

import pytest

from s3_insight.inventory import S3Inventory


class TestS3Inventory:
    """Test cases for S3Inventory class."""
    
    def test_init(self):
        """Test S3Inventory initialization."""
        inventory = S3Inventory(profile="test", sample_size=50000, verbose=True)
        assert inventory.profile == "test"
        assert inventory.sample_size == 50000
        assert inventory.verbose is True
        assert inventory.max_workers == 10
    
    def test_get_file_extension(self):
        """Test file extension extraction."""
        inventory = S3Inventory()
        
        # Test regular files
        assert inventory._get_file_extension("file.txt") == "txt"
        assert inventory._get_file_extension("image.jpg") == "jpg"
        assert inventory._get_file_extension("document.pdf") == "pdf"
        
        # Test files with multiple dots
        assert inventory._get_file_extension("file.backup.txt") == "txt"
        
        # Test files without extension
        assert inventory._get_file_extension("README") == "no-extension"
        assert inventory._get_file_extension("Dockerfile") == "no-extension"
        
        # Test directory-like keys
        assert inventory._get_file_extension("folder/") == "directory"
        assert inventory._get_file_extension("path/to/folder/") == "directory"
        
        # Test case sensitivity
        assert inventory._get_file_extension("file.TXT") == "txt"
        assert inventory._get_file_extension("image.JPG") == "jpg"
    
    def test_write_and_load_inventory(self):
        """Test writing and loading inventory data."""
        inventory = S3Inventory()
        
        # Sample inventory data
        test_data = {
            "bucket1": {
                "bucket_name": "bucket1",
                "object_count": 100,
                "total_size": 1024,
                "objects": []
            },
            "bucket2": {
                "bucket_name": "bucket2",
                "object_count": 200,
                "total_size": 2048,
                "objects": []
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            temp_file = f.name
        
        try:
            # Write inventory data
            inventory.write_inventory(test_data, temp_file)
            
            # Load inventory data
            loaded_data = inventory.load_inventory(temp_file)
            
            # Verify data
            assert len(loaded_data) == 2
            assert "bucket1" in loaded_data
            assert "bucket2" in loaded_data
            assert loaded_data["bucket1"]["object_count"] == 100
            assert loaded_data["bucket2"]["total_size"] == 2048
            
        finally:
            import os
            if os.path.exists(temp_file):
                os.unlink(temp_file)
    
    @patch('boto3.Session')
    def test_discover_buckets_success(self, mock_session):
        """Test successful bucket discovery."""
        # Mock S3 client response
        mock_s3_client = Mock()
        mock_s3_client.list_buckets.return_value = {
            'Buckets': [
                {'Name': 'bucket1', 'CreationDate': '2023-01-01'},
                {'Name': 'bucket2', 'CreationDate': '2023-01-02'},
            ]
        }
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_s3_client
        mock_session.return_value = mock_session_instance
        
        inventory = S3Inventory()
        buckets = inventory.discover_buckets()
        
        assert buckets == ['bucket1', 'bucket2']
        mock_s3_client.list_buckets.assert_called_once()
    
    @patch('boto3.Session')
    def test_discover_buckets_no_credentials(self, mock_session):
        """Test bucket discovery with no credentials."""
        from botocore.exceptions import NoCredentialsError
        
        mock_session_instance = Mock()
        mock_session_instance.client.side_effect = NoCredentialsError()
        mock_session.return_value = mock_session_instance
        
        inventory = S3Inventory()
        
        with pytest.raises(RuntimeError, match="Failed to discover buckets"):
            inventory.discover_buckets()
    
    @patch('boto3.Session')
    def test_inventory_bucket_access_denied(self, mock_session):
        """Test inventory collection with access denied."""
        from botocore.exceptions import ClientError
        
        # Mock S3 client that raises AccessDenied
        mock_s3_client = Mock()
        error_response = {
            'Error': {
                'Code': 'AccessDenied',
                'Message': 'Access Denied'
            }
        }
        mock_s3_client.get_bucket_location.side_effect = ClientError(
            error_response, 'GetBucketLocation'
        )
        
        mock_session_instance = Mock()
        mock_session_instance.client.return_value = mock_s3_client
        mock_session.return_value = mock_session_instance
        
        inventory = S3Inventory()
        result = inventory._inventory_bucket("test-bucket")
        
        assert result["bucket_name"] == "test-bucket"
        assert result["error"] == "Access denied"
        assert result["object_count"] == 0
        assert result["total_size"] == 0
        assert result["objects"] == [] 