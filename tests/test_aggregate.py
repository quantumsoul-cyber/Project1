"""Tests for the aggregate module."""

import pytest

from s3_insight.aggregate import S3Aggregator


class TestS3Aggregator:
    """Test cases for S3Aggregator class."""
    
    def test_init(self):
        """Test S3Aggregator initialization."""
        aggregator = S3Aggregator()
        assert aggregator is not None
    
    def test_compute_bucket_metrics(self):
        """Test bucket metrics computation."""
        aggregator = S3Aggregator()
        
        # Sample bucket data
        bucket_data = {
            "bucket_name": "test-bucket",
            "region": "us-east-1",
            "object_count": 1000,
            "total_size": 1024000,  # 1MB
            "storage_classes": {
                "STANDARD": 800,
                "STANDARD_IA": 200
            },
            "file_extensions": {
                "jpg": {"count": 500, "size": 512000},
                "pdf": {"count": 300, "size": 384000},
                "txt": {"count": 200, "size": 128000}
            },
            "age_buckets": {
                "recent": 600,
                "old": 400
            },
            "inventory_date": "2023-01-01T00:00:00"
        }
        
        metrics = aggregator._compute_bucket_metrics(bucket_data)
        
        # Test basic metrics
        assert metrics["bucket_name"] == "test-bucket"
        assert metrics["region"] == "us-east-1"
        assert metrics["object_count"] == 1000
        assert metrics["total_size"] == 1024000
        assert metrics["total_size_gb"] == 1024000 / (1024**3)
        assert metrics["total_size_tb"] == 1024000 / (1024**4)
        
        # Test average object size
        assert metrics["avg_object_size"] == 1024  # 1024000 / 1000
        assert metrics["avg_object_size_kb"] == 1.0  # 1024 / 1024
        
        # Test storage class breakdown
        assert "storage_class_breakdown" in metrics
        breakdown = metrics["storage_class_breakdown"]
        assert breakdown["STANDARD"]["count"] == 800
        assert breakdown["STANDARD"]["percentage"] == 80.0
        assert breakdown["STANDARD_IA"]["count"] == 200
        assert breakdown["STANDARD_IA"]["percentage"] == 20.0
        
        # Test age breakdown
        assert "age_breakdown" in metrics
        age_breakdown = metrics["age_breakdown"]
        assert age_breakdown["recent"]["count"] == 600
        assert age_breakdown["recent"]["percentage"] == 60.0
        assert age_breakdown["old"]["count"] == 400
        assert age_breakdown["old"]["percentage"] == 40.0
    
    def test_compute_bucket_metrics_zero_objects(self):
        """Test bucket metrics computation with zero objects."""
        aggregator = S3Aggregator()
        
        bucket_data = {
            "bucket_name": "empty-bucket",
            "region": "us-east-1",
            "object_count": 0,
            "total_size": 0,
            "storage_classes": {},
            "file_extensions": {},
            "age_buckets": {"recent": 0, "old": 0},
            "inventory_date": "2023-01-01T00:00:00"
        }
        
        metrics = aggregator._compute_bucket_metrics(bucket_data)
        
        assert metrics["avg_object_size"] == 0
        assert metrics["avg_object_size_kb"] == 0
        assert metrics["age_breakdown"]["recent"]["percentage"] == 0
        assert metrics["age_breakdown"]["old"]["percentage"] == 0
    
    def test_aggregate_buckets(self):
        """Test bucket aggregation."""
        aggregator = S3Aggregator()
        
        # Sample inventory data
        inventory_data = {
            "bucket1": {
                "bucket_name": "bucket1",
                "region": "us-east-1",
                "object_count": 100,
                "total_size": 1024000,
                "storage_classes": {"STANDARD": 100},
                "file_extensions": {"txt": {"count": 100, "size": 1024000}},
                "age_buckets": {"recent": 60, "old": 40},
                "inventory_date": "2023-01-01T00:00:00"
            },
            "bucket2": {
                "bucket_name": "bucket2",
                "region": "us-west-2",
                "object_count": 200,
                "total_size": 2048000,
                "storage_classes": {"STANDARD": 200},
                "file_extensions": {"jpg": {"count": 200, "size": 2048000}},
                "age_buckets": {"recent": 120, "old": 80},
                "inventory_date": "2023-01-01T00:00:00"
            }
        }
        
        bucket_metrics = aggregator.aggregate_buckets(inventory_data)
        
        assert len(bucket_metrics) == 2
        assert "bucket1" in bucket_metrics
        assert "bucket2" in bucket_metrics
        assert bucket_metrics["bucket1"]["object_count"] == 100
        assert bucket_metrics["bucket2"]["object_count"] == 200
    
    def test_aggregate_buckets_with_errors(self):
        """Test bucket aggregation with error buckets."""
        aggregator = S3Aggregator()
        
        inventory_data = {
            "bucket1": {
                "bucket_name": "bucket1",
                "object_count": 100,
                "total_size": 1024000,
                "storage_classes": {"STANDARD": 100},
                "file_extensions": {"txt": {"count": 100, "size": 1024000}},
                "age_buckets": {"recent": 60, "old": 40},
                "inventory_date": "2023-01-01T00:00:00"
            },
            "bucket2": {
                "error": "Access denied",
                "object_count": 0,
                "total_size": 0,
                "objects": []
            }
        }
        
        bucket_metrics = aggregator.aggregate_buckets(inventory_data)
        
        # Should only include bucket1 (bucket2 has error)
        assert len(bucket_metrics) == 1
        assert "bucket1" in bucket_metrics
        assert "bucket2" not in bucket_metrics
    
    def test_aggregate_account(self):
        """Test account-level aggregation."""
        aggregator = S3Aggregator()
        
        # Sample bucket metrics
        bucket_metrics = {
            "bucket1": {
                "bucket_name": "bucket1",
                "region": "us-east-1",
                "object_count": 100,
                "total_size": 1024000,
                "storage_classes": {"STANDARD": 100},
                "file_extensions": {"txt": {"count": 100, "size": 1024000}},
                "age_buckets": {"recent": 60, "old": 40},
                "sampled": False,
                "sample_size": 100
            },
            "bucket2": {
                "bucket_name": "bucket2",
                "region": "us-west-2",
                "object_count": 200,
                "total_size": 2048000,
                "storage_classes": {"STANDARD": 200},
                "file_extensions": {"jpg": {"count": 200, "size": 2048000}},
                "age_buckets": {"recent": 120, "old": 80},
                "sampled": True,
                "sample_size": 100000
            }
        }
        
        account_metrics = aggregator.aggregate_account(bucket_metrics)
        
        # Test basic metrics
        assert account_metrics["bucket_count"] == 2
        assert account_metrics["total_objects"] == 300
        assert account_metrics["total_size"] == 3072000
        assert account_metrics["avg_object_size"] == 10240  # 3072000 / 300
        assert account_metrics["avg_object_size_kb"] == 10.0  # 10240 / 1024
        
        # Test regions
        assert account_metrics["regions"]["us-east-1"] == 1
        assert account_metrics["regions"]["us-west-2"] == 1
        
        # Test sampled buckets
        assert account_metrics["sampled_buckets"] == 1
        
        # Test age buckets
        assert account_metrics["age_buckets"]["recent"] == 180
        assert account_metrics["age_buckets"]["old"] == 120
    
    def test_get_top_buckets(self):
        """Test getting top buckets."""
        aggregator = S3Aggregator()
        
        bucket_metrics = {
            "small-bucket": {"total_size": 1000, "object_count": 10},
            "medium-bucket": {"total_size": 5000, "object_count": 50},
            "large-bucket": {"total_size": 10000, "object_count": 100}
        }
        
        # Test top 2 by size
        top_buckets = aggregator.get_top_buckets(bucket_metrics, top_n=2, sort_by="total_size")
        assert len(top_buckets) == 2
        assert top_buckets[0]["bucket_name"] == "large-bucket"
        assert top_buckets[1]["bucket_name"] == "medium-bucket"
        
        # Test top 2 by object count
        top_buckets = aggregator.get_top_buckets(bucket_metrics, top_n=2, sort_by="object_count")
        assert len(top_buckets) == 2
        assert top_buckets[0]["bucket_name"] == "large-bucket"
        assert top_buckets[1]["bucket_name"] == "medium-bucket"
    
    def test_get_top_extensions(self):
        """Test getting top extensions."""
        aggregator = S3Aggregator()
        
        account_metrics = {
            "file_extensions": {
                "txt": {"count": 100, "size": 1000},
                "jpg": {"count": 200, "size": 2000},
                "pdf": {"count": 50, "size": 500}
            }
        }
        
        top_extensions = aggregator.get_top_extensions(account_metrics, top_n=2)
        assert len(top_extensions) == 2
        assert top_extensions[0]["extension"] == "jpg"
        assert top_extensions[1]["extension"] == "txt" 