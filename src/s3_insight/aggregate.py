"""S3 inventory data aggregation and metrics computation."""

from typing import Any, Dict, List


class S3Aggregator:
    """Aggregates S3 inventory data and computes metrics."""
    
    def aggregate_buckets(self, inventory_data: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate inventory data into per-bucket metrics.
        
        Args:
            inventory_data: Raw inventory data from S3Inventory
            
        Returns:
            Dictionary with aggregated bucket metrics
        """
        bucket_metrics = {}
        
        for bucket_name, bucket_data in inventory_data.items():
            if "error" in bucket_data:
                # Skip buckets with errors
                continue
                
            metrics = self._compute_bucket_metrics(bucket_data)
            bucket_metrics[bucket_name] = metrics
        
        return bucket_metrics
    
    def aggregate_account(self, bucket_metrics: Dict[str, Any]) -> Dict[str, Any]:
        """Aggregate bucket metrics into account-level summary.
        
        Args:
            bucket_metrics: Per-bucket metrics from aggregate_buckets
            
        Returns:
            Dictionary with account-level metrics
        """
        account_metrics = {
            "bucket_count": len(bucket_metrics),
            "total_objects": 0,
            "total_size": 0,
            "storage_classes": {},
            "file_extensions": {},
            "age_buckets": {"recent": 0, "old": 0},
            "regions": {},
            "sampled_buckets": 0,
        }
        
        for bucket_name, metrics in bucket_metrics.items():
            # Sum basic metrics
            account_metrics["total_objects"] += metrics["object_count"]
            account_metrics["total_size"] += metrics["total_size"]
            
            # Track regions
            region = metrics["region"]
            account_metrics["regions"][region] = account_metrics["regions"].get(region, 0) + 1
            
            # Track sampled buckets
            if metrics["sampled"]:
                account_metrics["sampled_buckets"] += 1
            
            # Aggregate storage classes
            for storage_class, count in metrics["storage_classes"].items():
                if storage_class not in account_metrics["storage_classes"]:
                    account_metrics["storage_classes"][storage_class] = {
                        "count": 0,
                        "size": 0,
                        "size_gb": 0
                    }
                account_metrics["storage_classes"][storage_class]["count"] += count
                
                # Estimate size for this storage class (proportional to object count)
                if metrics["object_count"] > 0:
                    avg_object_size = metrics["total_size"] / metrics["object_count"]
                    estimated_size = count * avg_object_size
                    account_metrics["storage_classes"][storage_class]["size"] += estimated_size
                    account_metrics["storage_classes"][storage_class]["size_gb"] = (
                        account_metrics["storage_classes"][storage_class]["size"] / (1024**3)
                    )
            
            # Aggregate file extensions
            for ext, ext_data in metrics["file_extensions"].items():
                if ext not in account_metrics["file_extensions"]:
                    account_metrics["file_extensions"][ext] = {
                        "count": 0,
                        "size": 0,
                        "size_gb": 0
                    }
                account_metrics["file_extensions"][ext]["count"] += ext_data["count"]
                account_metrics["file_extensions"][ext]["size"] += ext_data["size"]
                account_metrics["file_extensions"][ext]["size_gb"] = (
                    account_metrics["file_extensions"][ext]["size"] / (1024**3)
                )
            
            # Aggregate age buckets
            account_metrics["age_buckets"]["recent"] += metrics["age_buckets"]["recent"]
            account_metrics["age_buckets"]["old"] += metrics["age_buckets"]["old"]
        
        # Compute derived metrics
        if account_metrics["total_objects"] > 0:
            account_metrics["avg_object_size"] = account_metrics["total_size"] / account_metrics["total_objects"]
            account_metrics["avg_object_size_kb"] = account_metrics["avg_object_size"] / 1024
        else:
            account_metrics["avg_object_size"] = 0
            account_metrics["avg_object_size_kb"] = 0
        
        account_metrics["total_size_gb"] = account_metrics["total_size"] / (1024**3)
        account_metrics["total_size_tb"] = account_metrics["total_size"] / (1024**4)
        
        # Sort file extensions by count
        account_metrics["file_extensions"] = dict(
            sorted(
                account_metrics["file_extensions"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )
        )
        
        return account_metrics
    
    def _compute_bucket_metrics(self, bucket_data: Dict[str, Any]) -> Dict[str, Any]:
        """Compute metrics for a single bucket.
        
        Args:
            bucket_data: Raw bucket inventory data
            
        Returns:
            Dictionary with computed bucket metrics
        """
        object_count = bucket_data["object_count"]
        total_size = bucket_data["total_size"]
        
        metrics = {
            "bucket_name": bucket_data["bucket_name"],
            "region": bucket_data["region"],
            "object_count": object_count,
            "total_size": total_size,
            "total_size_gb": total_size / (1024**3),
            "total_size_tb": total_size / (1024**4),
            "sampled": bucket_data.get("sampled", False),
            "sample_size": bucket_data.get("sample_size", object_count),
            "storage_classes": bucket_data["storage_classes"],
            "file_extensions": bucket_data["file_extensions"],
            "age_buckets": bucket_data["age_buckets"],
            "inventory_date": bucket_data["inventory_date"],
        }
        
        # Compute average object size
        if object_count > 0:
            metrics["avg_object_size"] = total_size / object_count
            metrics["avg_object_size_kb"] = metrics["avg_object_size"] / 1024
        else:
            metrics["avg_object_size"] = 0
            metrics["avg_object_size_kb"] = 0
        
        # Add storage class breakdown with sizes
        storage_class_breakdown = {}
        for storage_class, count in bucket_data["storage_classes"].items():
            if object_count > 0:
                avg_object_size = total_size / object_count
                estimated_size = count * avg_object_size
                storage_class_breakdown[storage_class] = {
                    "count": count,
                    "size": estimated_size,
                    "size_gb": estimated_size / (1024**3),
                    "percentage": (count / object_count) * 100
                }
            else:
                storage_class_breakdown[storage_class] = {
                    "count": 0,
                    "size": 0,
                    "size_gb": 0,
                    "percentage": 0
                }
        
        metrics["storage_class_breakdown"] = storage_class_breakdown
        
        # Add age breakdown percentages
        total_objects = bucket_data["age_buckets"]["recent"] + bucket_data["age_buckets"]["old"]
        if total_objects > 0:
            metrics["age_breakdown"] = {
                "recent": {
                    "count": bucket_data["age_buckets"]["recent"],
                    "percentage": (bucket_data["age_buckets"]["recent"] / total_objects) * 100
                },
                "old": {
                    "count": bucket_data["age_buckets"]["old"],
                    "percentage": (bucket_data["age_buckets"]["old"] / total_objects) * 100
                }
            }
        else:
            metrics["age_breakdown"] = {
                "recent": {"count": 0, "percentage": 0},
                "old": {"count": 0, "percentage": 0}
            }
        
        return metrics
    
    def get_top_buckets(self, bucket_metrics: Dict[str, Any], top_n: int = 10, sort_by: str = "total_size") -> List[Dict[str, Any]]:
        """Get top N buckets sorted by specified metric.
        
        Args:
            bucket_metrics: Per-bucket metrics
            top_n: Number of top buckets to return
            sort_by: Metric to sort by (total_size, object_count, avg_object_size)
            
        Returns:
            List of top bucket metrics
        """
        sorted_buckets = sorted(
            bucket_metrics.items(),
            key=lambda x: x[1][sort_by],
            reverse=True
        )[:top_n]
        
        return [{"bucket_name": name, **metrics} for name, metrics in sorted_buckets]
    
    def get_top_extensions(self, account_metrics: Dict[str, Any], top_n: int = 10) -> List[Dict[str, Any]]:
        """Get top N file extensions.
        
        Args:
            account_metrics: Account-level metrics
            top_n: Number of top extensions to return
            
        Returns:
            List of top extension metrics
        """
        sorted_extensions = sorted(
            account_metrics["file_extensions"].items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:top_n]
        
        return [{"extension": ext, **data} for ext, data in sorted_extensions] 