"""Report format writers for S3 inventory data."""

import csv
import json
import os
from datetime import datetime
from typing import Any, Dict, List


class ReportWriter:
    """Writes S3 inventory reports in various formats."""
    
    def __init__(self, output_dir: str = "reports") -> None:
        """Initialize the report writer.
        
        Args:
            output_dir: Directory to save reports
        """
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
    
    def write_reports(
        self,
        bucket_metrics: Dict[str, Any],
        account_metrics: Dict[str, Any],
        charts: Dict[str, str],
        output_dir: str = None
    ) -> Dict[str, str]:
        """Write all report formats.
        
        Args:
            bucket_metrics: Per-bucket metrics
            account_metrics: Account-level metrics
            charts: Dictionary of chart file paths
            output_dir: Override output directory
            
        Returns:
            Dictionary mapping report types to file paths
        """
        if output_dir:
            self.output_dir = output_dir
            os.makedirs(output_dir, exist_ok=True)
        
        report_files = {}
        
        # Write CSV report
        report_files["csv"] = self._write_csv_report(bucket_metrics)
        
        # Write JSON report
        report_files["json"] = self._write_json_report(account_metrics)
        
        # Write Markdown report
        report_files["markdown"] = self._write_markdown_report(
            bucket_metrics, account_metrics, charts
        )
        
        return report_files
    
    def _write_csv_report(self, bucket_metrics: Dict[str, Any]) -> str:
        """Write bucket metrics to CSV file.
        
        Args:
            bucket_metrics: Per-bucket metrics
            
        Returns:
            Path to CSV file
        """
        filename = os.path.join(self.output_dir, "report-buckets.csv")
        
        with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
            fieldnames = [
                'bucket_name',
                'region',
                'object_count',
                'total_size_bytes',
                'total_size_gb',
                'total_size_tb',
                'avg_object_size_bytes',
                'avg_object_size_kb',
                'sampled',
                'sample_size',
                'storage_classes',
                'top_extensions',
                'recent_objects',
                'old_objects',
                'recent_percentage',
                'old_percentage',
                'inventory_date'
            ]
            
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            writer.writeheader()
            
            for bucket_name, metrics in bucket_metrics.items():
                row = {
                    'bucket_name': bucket_name,
                    'region': metrics['region'],
                    'object_count': metrics['object_count'],
                    'total_size_bytes': metrics['total_size'],
                    'total_size_gb': f"{metrics['total_size_gb']:.2f}",
                    'total_size_tb': f"{metrics['total_size_tb']:.3f}",
                    'avg_object_size_bytes': metrics['avg_object_size'],
                    'avg_object_size_kb': f"{metrics['avg_object_size_kb']:.2f}",
                    'sampled': metrics['sampled'],
                    'sample_size': metrics['sample_size'],
                    'storage_classes': json.dumps(metrics['storage_classes']),
                    'top_extensions': json.dumps(dict(list(metrics['file_extensions'].items())[:5])),
                    'recent_objects': metrics['age_buckets']['recent'],
                    'old_objects': metrics['age_buckets']['old'],
                    'recent_percentage': f"{metrics['age_breakdown']['recent']['percentage']:.1f}",
                    'old_percentage': f"{metrics['age_breakdown']['old']['percentage']:.1f}",
                    'inventory_date': metrics['inventory_date']
                }
                writer.writerow(row)
        
        return filename
    
    def _write_json_report(self, account_metrics: Dict[str, Any]) -> str:
        """Write account metrics to JSON file.
        
        Args:
            account_metrics: Account-level metrics
            
        Returns:
            Path to JSON file
        """
        filename = os.path.join(self.output_dir, "report-account.json")
        
        # Add report metadata
        report_data = {
            "report_metadata": {
                "generated_at": datetime.now().isoformat(),
                "tool_version": "s3-insight-0.1.0",
                "report_type": "account_summary"
            },
            "account_metrics": account_metrics
        }
        
        with open(filename, 'w', encoding='utf-8') as jsonfile:
            json.dump(report_data, jsonfile, indent=2, ensure_ascii=False)
        
        return filename
    
    def _write_markdown_report(
        self,
        bucket_metrics: Dict[str, Any],
        account_metrics: Dict[str, Any],
        charts: Dict[str, str]
    ) -> str:
        """Write comprehensive Markdown report.
        
        Args:
            bucket_metrics: Per-bucket metrics
            account_metrics: Account-level metrics
            charts: Dictionary of chart file paths
            
        Returns:
            Path to Markdown file
        """
        filename = os.path.join(self.output_dir, "report.md")
        
        with open(filename, 'w', encoding='utf-8') as mdfile:
            # Header
            mdfile.write("# S3 Inventory Report\n\n")
            mdfile.write(f"**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}\n")
            mdfile.write(f"**Tool Version:** s3-insight-0.1.0\n\n")
            
            # Executive Summary
            mdfile.write("## Executive Summary\n\n")
            mdfile.write(f"- **Total Buckets:** {account_metrics['bucket_count']:,}\n")
            mdfile.write(f"- **Total Objects:** {account_metrics['total_objects']:,}\n")
            mdfile.write(f"- **Total Size:** {account_metrics['total_size_gb']:.2f} GB ({account_metrics['total_size_tb']:.3f} TB)\n")
            mdfile.write(f"- **Average Object Size:** {account_metrics['avg_object_size_kb']:.2f} KB\n")
            if account_metrics['sampled_buckets'] > 0:
                mdfile.write(f"- **Sampled Buckets:** {account_metrics['sampled_buckets']} (large buckets >100M objects)\n")
            mdfile.write("\n")
            
            # Charts section
            if charts:
                mdfile.write("## Visualizations\n\n")
                for chart_name, chart_path in charts.items():
                    chart_filename = os.path.basename(chart_path)
                    mdfile.write(f"### {self._format_chart_title(chart_name)}\n\n")
                    mdfile.write(f"![{chart_name}]({chart_filename})\n\n")
            
            # Account-level metrics
            mdfile.write("## Account-Level Metrics\n\n")
            
            # Storage classes
            if account_metrics['storage_classes']:
                mdfile.write("### Storage Class Distribution\n\n")
                mdfile.write("| Storage Class | Objects | Size (GB) | % Objects | % Size |\n")
                mdfile.write("|---------------|---------|-----------|-----------|--------|\n")
                
                total_objects = account_metrics['total_objects']
                total_size = account_metrics['total_size']
                
                for storage_class, data in account_metrics['storage_classes'].items():
                    obj_pct = (data['count'] / total_objects * 100) if total_objects > 0 else 0
                    size_pct = (data['size'] / total_size * 100) if total_size > 0 else 0
                    mdfile.write(
                        f"| {storage_class} | {data['count']:,} | {data['size_gb']:.2f} | "
                        f"{obj_pct:.1f}% | {size_pct:.1f}% |\n"
                    )
                mdfile.write("\n")
            
            # File extensions
            if account_metrics['file_extensions']:
                mdfile.write("### Top File Extensions\n\n")
                mdfile.write("| Extension | Objects | Size (GB) | % Objects | % Size |\n")
                mdfile.write("|-----------|---------|-----------|-----------|--------|\n")
                
                top_extensions = list(account_metrics['file_extensions'].items())[:10]
                for ext, data in top_extensions:
                    ext_name = ext if ext != "no-extension" else "No Extension"
                    obj_pct = (data['count'] / total_objects * 100) if total_objects > 0 else 0
                    size_pct = (data['size'] / total_size * 100) if total_size > 0 else 0
                    mdfile.write(
                        f"| {ext_name} | {data['count']:,} | {data['size_gb']:.2f} | "
                        f"{obj_pct:.1f}% | {size_pct:.1f}% |\n"
                    )
                mdfile.write("\n")
            
            # Age distribution
            if account_metrics['age_buckets']['recent'] > 0 or account_metrics['age_buckets']['old'] > 0:
                mdfile.write("### Object Age Distribution\n\n")
                mdfile.write("| Age Category | Objects | Percentage |\n")
                mdfile.write("|--------------|---------|------------|\n")
                
                recent = account_metrics['age_buckets']['recent']
                old = account_metrics['age_buckets']['old']
                total_age_objects = recent + old
                
                if total_age_objects > 0:
                    recent_pct = (recent / total_age_objects * 100)
                    old_pct = (old / total_age_objects * 100)
                    mdfile.write(f"| Recent (≤30 days) | {recent:,} | {recent_pct:.1f}% |\n")
                    mdfile.write(f"| Old (>30 days) | {old:,} | {old_pct:.1f}% |\n")
                mdfile.write("\n")
            
            # Region distribution
            if account_metrics['regions']:
                mdfile.write("### Bucket Distribution by Region\n\n")
                mdfile.write("| Region | Buckets | Percentage |\n")
                mdfile.write("|--------|---------|------------|\n")
                
                total_buckets = account_metrics['bucket_count']
                for region, count in account_metrics['regions'].items():
                    pct = (count / total_buckets * 100) if total_buckets > 0 else 0
                    mdfile.write(f"| {region} | {count} | {pct:.1f}% |\n")
                mdfile.write("\n")
            
            # Per-bucket details
            mdfile.write("## Per-Bucket Details\n\n")
            mdfile.write("| Bucket | Region | Objects | Size (GB) | Avg Size (KB) | Storage Classes |\n")
            mdfile.write("|--------|--------|---------|-----------|---------------|-----------------|\n")
            
            # Sort buckets by size
            sorted_buckets = sorted(
                bucket_metrics.items(),
                key=lambda x: x[1]['total_size'],
                reverse=True
            )
            
            for bucket_name, metrics in sorted_buckets:
                storage_classes_str = ", ".join(metrics['storage_classes'].keys())
                mdfile.write(
                    f"| {bucket_name} | {metrics['region']} | {metrics['object_count']:,} | "
                    f"{metrics['total_size_gb']:.2f} | {metrics['avg_object_size_kb']:.2f} | "
                    f"{storage_classes_str} |\n"
                )
            
            mdfile.write("\n")
            
            # Footer
            mdfile.write("---\n\n")
            mdfile.write("*Report generated by S3-Insight*\n")
        
        return filename
    
    def _format_chart_title(self, chart_name: str) -> str:
        """Format chart name for display.
        
        Args:
            chart_name: Raw chart name
            
        Returns:
            Formatted chart title
        """
        title_map = {
            "filetype_pie": "File Type Distribution",
            "storageclass_bar": "Storage Class Distribution",
            "top_buckets_bar": "Top Buckets by Size",
            "age_distribution_pie": "Object Age Distribution",
            "region_distribution_pie": "Bucket Distribution by Region"
        }
        
        return title_map.get(chart_name, chart_name.replace('_', ' ').title()) 