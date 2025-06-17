#!/usr/bin/env python3
"""
Basic usage example for S3-Insight.

This script demonstrates how to use the S3-Insight library programmatically
to collect inventory data and generate reports.
"""

import os
import sys
from pathlib import Path

# Add the src directory to the Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from s3_insight.inventory import S3Inventory
from s3_insight.aggregate import S3Aggregator
from s3_insight.charts import ChartGenerator
from s3_insight.formats import ReportWriter
from s3_insight.utils import get_aws_account_id


def main():
    """Run the basic usage example."""
    print("🚀 S3-Insight Basic Usage Example")
    print("=" * 50)
    
    # Configuration
    aws_profile = os.getenv("AWS_PROFILE", None)
    output_dir = "example_output"
    
    try:
        # Step 1: Get AWS account ID
        print("\n📋 Step 1: Getting AWS account ID...")
        account_id = get_aws_account_id(aws_profile)
        print(f"   Account ID: {account_id}")
        
        # Step 2: Initialize inventory collector
        print("\n🔍 Step 2: Initializing inventory collector...")
        inventory = S3Inventory(
            profile=aws_profile,
            sample_size=1000,  # Small sample for demo
            verbose=True
        )
        
        # Step 3: Discover buckets
        print("\n📦 Step 3: Discovering S3 buckets...")
        buckets = inventory.discover_buckets()
        print(f"   Found {len(buckets)} buckets")
        
        if not buckets:
            print("   No buckets found or no access to S3")
            return
        
        # Step 4: Collect inventory (for demo, just use first bucket)
        print(f"\n📊 Step 4: Collecting inventory for first bucket...")
        demo_bucket = buckets[0]
        print(f"   Analyzing bucket: {demo_bucket}")
        
        # For demo purposes, create mock data instead of real inventory
        mock_inventory_data = {
            demo_bucket: {
                "bucket_name": demo_bucket,
                "region": "us-east-1",
                "object_count": 1500,
                "total_size": 1024 * 1024 * 100,  # 100MB
                "sampled": False,
                "sample_size": 1500,
                "storage_classes": {
                    "STANDARD": 1200,
                    "STANDARD_IA": 300
                },
                "file_extensions": {
                    "jpg": {"count": 800, "size": 50 * 1024 * 1024},
                    "pdf": {"count": 400, "size": 30 * 1024 * 1024},
                    "txt": {"count": 200, "size": 10 * 1024 * 1024},
                    "mp4": {"count": 100, "size": 10 * 1024 * 1024}
                },
                "age_buckets": {
                    "recent": 900,
                    "old": 600
                },
                "objects": [],
                "inventory_date": "2023-12-01T12:00:00"
            }
        }
        
        # Step 5: Aggregate data
        print("\n📈 Step 5: Aggregating metrics...")
        aggregator = S3Aggregator()
        bucket_metrics = aggregator.aggregate_buckets(mock_inventory_data)
        account_metrics = aggregator.aggregate_account(bucket_metrics)
        
        print(f"   Total objects: {account_metrics['total_objects']:,}")
        print(f"   Total size: {account_metrics['total_size_gb']:.2f} GB")
        print(f"   Average object size: {account_metrics['avg_object_size_kb']:.2f} KB")
        
        # Step 6: Generate charts
        print("\n📊 Step 6: Generating charts...")
        os.makedirs(output_dir, exist_ok=True)
        chart_gen = ChartGenerator(output_dir=output_dir)
        charts = chart_gen.generate_charts(bucket_metrics, account_metrics, top_extensions=5)
        
        print(f"   Generated {len(charts)} charts:")
        for chart_name, chart_path in charts.items():
            print(f"     - {chart_name}: {os.path.basename(chart_path)}")
        
        # Step 7: Generate reports
        print("\n📋 Step 7: Generating reports...")
        writer = ReportWriter(output_dir=output_dir)
        report_files = writer.write_reports(bucket_metrics, account_metrics, charts)
        
        print(f"   Generated {len(report_files)} reports:")
        for report_type, report_path in report_files.items():
            print(f"     - {report_type}: {os.path.basename(report_path)}")
        
        # Step 8: Display summary
        print("\n✅ Example completed successfully!")
        print(f"📁 Output directory: {output_dir}")
        print("\n📊 Summary:")
        print(f"   - Buckets analyzed: {len(buckets)}")
        print(f"   - Total objects: {account_metrics['total_objects']:,}")
        print(f"   - Total storage: {account_metrics['total_size_gb']:.2f} GB")
        print(f"   - Storage classes: {len(account_metrics['storage_classes'])}")
        print(f"   - File types: {len(account_metrics['file_extensions'])}")
        
        # Show top file extensions
        if account_metrics['file_extensions']:
            print("\n📁 Top file extensions:")
            top_exts = list(account_metrics['file_extensions'].items())[:3]
            for ext, data in top_exts:
                ext_name = ext if ext != "no-extension" else "No Extension"
                print(f"   - {ext_name}: {data['count']:,} objects ({data['size_gb']:.2f} GB)")
        
        print(f"\n🎯 Next steps:")
        print(f"   1. Check the '{output_dir}' directory for generated files")
        print(f"   2. Run 's3-insight inventory' for real inventory collection")
        print(f"   3. Run 's3-insight report --upload' to publish to S3")
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        print("\n💡 Make sure you have:")
        print("   - AWS credentials configured")
        print("   - Appropriate S3 permissions")
        print("   - Python dependencies installed")
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main()) 