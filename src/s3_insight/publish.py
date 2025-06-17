"""S3 report publishing module."""

import json
import os
from datetime import datetime
from typing import Dict, List, Optional

import boto3
from botocore.exceptions import ClientError, NoCredentialsError


class S3Publisher:
    """Handles uploading reports to S3 reports bucket."""
    
    def __init__(self, profile: Optional[str] = None) -> None:
        """Initialize the S3 publisher.
        
        Args:
            profile: AWS profile to use
        """
        self.profile = profile
        self.session = self._create_session()
        self.account_id = self._get_account_id()
        self.reports_bucket = f"s3-insight-reports-{self.account_id}"
    
    def _create_session(self) -> boto3.Session:
        """Create boto3 session with profile if specified."""
        if self.profile:
            return boto3.Session(profile_name=self.profile)
        return boto3.Session()
    
    def _get_account_id(self) -> str:
        """Get AWS account ID."""
        try:
            sts_client = self.session.client('sts')
            response = sts_client.get_caller_identity()
            return response['Account']
        except (NoCredentialsError, ClientError) as e:
            raise RuntimeError(f"Failed to get account ID: {e}")
    
    def publish_reports(self, report_files: Dict[str, str]) -> List[str]:
        """Upload all report files to S3 reports bucket.
        
        Args:
            report_files: Dictionary mapping report types to file paths
            
        Returns:
            List of S3 URLs for uploaded files
        """
        # Ensure reports bucket exists
        self._ensure_reports_bucket()
        
        upload_urls = []
        
        for report_type, filepath in report_files.items():
            if os.path.exists(filepath):
                url = self._upload_file(filepath, report_type)
                upload_urls.append(url)
        
        # Upload charts if they exist
        charts_dir = os.path.dirname(list(report_files.values())[0]) if report_files else "charts"
        if os.path.exists(charts_dir):
            chart_files = self._get_chart_files(charts_dir)
            for chart_file in chart_files:
                url = self._upload_file(chart_file, "charts")
                upload_urls.append(url)
        
        return upload_urls
    
    def _ensure_reports_bucket(self) -> None:
        """Create reports bucket if it doesn't exist."""
        try:
            s3_client = self.session.client('s3')
            
            # Check if bucket exists
            try:
                s3_client.head_bucket(Bucket=self.reports_bucket)
                return  # Bucket exists
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code == '404':
                    # Bucket doesn't exist, create it
                    pass
                else:
                    raise
            
            # Create bucket in us-east-1 (default)
            s3_client.create_bucket(Bucket=self.reports_bucket)
            
            # Add bucket policy for public read access to reports
            bucket_policy = {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "PublicReadGetObject",
                        "Effect": "Allow",
                        "Principal": "*",
                        "Action": "s3:GetObject",
                        "Resource": f"arn:aws:s3:::{self.reports_bucket}/*"
                    }
                ]
            }
            
            s3_client.put_bucket_policy(
                Bucket=self.reports_bucket,
                Policy=json.dumps(bucket_policy)
            )
            
            # Enable static website hosting
            s3_client.put_bucket_website(
                Bucket=self.reports_bucket,
                WebsiteConfiguration={
                    'IndexDocument': {'Suffix': 'index.html'},
                    'ErrorDocument': {'Key': 'error.html'}
                }
            )
            
        except ClientError as e:
            raise RuntimeError(f"Failed to create reports bucket: {e}")
    
    def _upload_file(self, filepath: str, file_type: str) -> str:
        """Upload a single file to S3 reports bucket.
        
        Args:
            filepath: Local file path
            file_type: Type of file (reports, charts, etc.)
            
        Returns:
            S3 URL of uploaded file
        """
        try:
            s3_client = self.session.client('s3')
            
            # Determine S3 key
            filename = os.path.basename(filepath)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            s3_key = f"{file_type}/{timestamp}/{filename}"
            
            # Upload file
            s3_client.upload_file(
                filepath,
                self.reports_bucket,
                s3_key,
                ExtraArgs={
                    'ContentType': self._get_content_type(filename),
                    'ACL': 'public-read'
                }
            )
            
            # Return public URL
            url = f"https://{self.reports_bucket}.s3.amazonaws.com/{s3_key}"
            return url
            
        except ClientError as e:
            raise RuntimeError(f"Failed to upload {filepath}: {e}")
    
    def _get_chart_files(self, charts_dir: str) -> List[str]:
        """Get list of chart files in charts directory.
        
        Args:
            charts_dir: Directory containing chart files
            
        Returns:
            List of chart file paths
        """
        chart_files = []
        for filename in os.listdir(charts_dir):
            if filename.endswith('.png'):
                chart_files.append(os.path.join(charts_dir, filename))
        return chart_files
    
    def _get_content_type(self, filename: str) -> str:
        """Get content type for file based on extension.
        
        Args:
            filename: File name
            
        Returns:
            Content type string
        """
        ext = os.path.splitext(filename)[1].lower()
        content_types = {
            '.csv': 'text/csv',
            '.json': 'application/json',
            '.md': 'text/markdown',
            '.png': 'image/png',
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.html': 'text/html',
        }
        return content_types.get(ext, 'application/octet-stream')
    
    def create_index_page(self, report_urls: List[str]) -> str:
        """Create and upload an index page for the reports.
        
        Args:
            report_urls: List of S3 URLs for uploaded reports
            
        Returns:
            URL of the index page
        """
        html_content = self._generate_index_html(report_urls)
        
        # Save to temporary file
        index_file = "index.html"
        with open(index_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        try:
            # Upload index file
            s3_client = self.session.client('s3')
            s3_client.upload_file(
                index_file,
                self.reports_bucket,
                'index.html',
                ExtraArgs={
                    'ContentType': 'text/html',
                    'ACL': 'public-read'
                }
            )
            
            # Return index URL
            index_url = f"https://{self.reports_bucket}.s3-website-us-east-1.amazonaws.com/"
            return index_url
            
        finally:
            # Clean up temporary file
            if os.path.exists(index_file):
                os.remove(index_file)
    
    def _generate_index_html(self, report_urls: List[str]) -> str:
        """Generate HTML index page for reports.
        
        Args:
            report_urls: List of S3 URLs for uploaded reports
            
        Returns:
            HTML content
        """
        html = f"""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>S3-Insight Reports</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            border-radius: 10px;
            margin-bottom: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .reports-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .report-card {{
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }}
        .report-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 4px 20px rgba(0,0,0,0.15);
        }}
        .report-card h3 {{
            margin: 0 0 10px 0;
            color: #333;
        }}
        .report-card p {{
            margin: 0 0 15px 0;
            color: #666;
            font-size: 0.9em;
        }}
        .report-link {{
            display: inline-block;
            background: #667eea;
            color: white;
            text-decoration: none;
            padding: 8px 16px;
            border-radius: 5px;
            font-size: 0.9em;
            transition: background 0.2s;
        }}
        .report-link:hover {{
            background: #5a6fd8;
        }}
        .footer {{
            text-align: center;
            color: #666;
            margin-top: 40px;
            padding: 20px;
            border-top: 1px solid #ddd;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>📊 S3-Insight Reports</h1>
        <p>Comprehensive AWS S3 bucket inventory and analytics</p>
        <p>Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S UTC')}</p>
    </div>
    
    <div class="reports-grid">
"""
        
        # Group reports by type
        reports_by_type = {}
        for url in report_urls:
            if '/reports/' in url:
                reports_by_type.setdefault('Reports', []).append(url)
            elif '/charts/' in url:
                reports_by_type.setdefault('Charts', []).append(url)
        
        # Generate cards for each report type
        for report_type, urls in reports_by_type.items():
            html += f"""
        <div class="report-card">
            <h3>{report_type}</h3>
            <p>Download and view {report_type.lower()} generated from S3 inventory data.</p>
"""
            
            for url in urls:
                filename = url.split('/')[-1]
                html += f'            <a href="{url}" class="report-link" target="_blank">{filename}</a><br><br>\n'
            
            html += "        </div>\n"
        
        html += """
    </div>
    
    <div class="footer">
        <p>Generated by <strong>S3-Insight</strong> - AWS S3 bucket inventory and analytics tool</p>
    </div>
</body>
</html>
"""
        
        return html 