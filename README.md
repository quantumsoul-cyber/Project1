# S3-Insight

A comprehensive Python CLI tool for AWS S3 bucket inventory and analytics. S3-Insight provides detailed insights into your S3 storage usage, including object counts, file type distributions, storage class breakdowns, and cost analysis.

## Features

- **🔍 Complete S3 Inventory**: Discover and analyze all S3 buckets in your AWS account
- **📊 Rich Analytics**: Object counts, total bytes, average object sizes, file type distributions
- **🎯 Smart Sampling**: Automatic sampling for large buckets (>100M objects) to improve performance
- **📈 Visual Charts**: Auto-generated pie charts and bar charts using Matplotlib
- **📋 Multiple Formats**: Export reports in CSV, JSON, and Markdown formats
- **📊 Comprehensive Dashboard**: Single image with all charts combined for presentations
- **☁️ S3 Publishing**: Automatically upload reports to a dedicated S3 reports bucket
- **💰 Cost Analysis**: Storage class breakdown and cost estimation
- **⏰ Age Analysis**: Object age distribution (recent vs. old objects)
- **🌍 Regional Insights**: Bucket distribution across AWS regions

## Installation

### Prerequisites

- Python 3.9 or higher
- AWS CLI v2 configured with appropriate credentials
- AWS permissions: `s3:List*`, `s3:GetBucketLocation`, `s3:PutObject`

### Install from Source

```bash
# Clone the repository
git clone https://github.com/quantumsoul-cyber/Project1.git
cd Project1

# Install in development mode
pip install -e .

# Or install with development dependencies
pip install -e ".[dev]"
```

### Install Dependencies

```bash
pip install -r requirements.txt
```

## Quick Start

### Prerequisites

- Python 3.9 or higher
- AWS CLI v2 configured with appropriate credentials
- AWS permissions: `s3:List*`, `s3:GetBucketLocation`, `s3:PutObject`

### Installation

```bash
# Clone the repository
git clone https://github.com/quantumsoul-cyber/Project1.git
cd Project1

# Install in development mode
pip install -e .
```

### Basic Usage

**📝 Important Note**: By default, S3-Insight saves files to your home directory (`~`) to avoid permission issues. Make sure to run commands from the appropriate directory or specify full paths.

#### 1. Collect S3 Inventory

```bash
# Collect inventory data (saves to ~/inventory.jsonl)
s3-insight inventory

# With specific AWS profile
s3-insight inventory --profile production

# Custom output location
s3-insight inventory --output ~/my-inventory.jsonl
```

#### 2. Generate Reports and Charts

```bash
# Generate all reports and charts (reads from ~/inventory.jsonl, saves to ~/reports)
s3-insight report

# Generate just the comprehensive dashboard
s3-insight dashboard

# Upload reports to S3
s3-insight report --upload

# Custom output directory
s3-insight report --output-dir my-reports

# Specify number of top extensions to show
s3-insight report --top-extensions 15
```

#### 3. View Quick Statistics

```bash
# Display account overview (reads from ~/inventory.jsonl)
s3-insight stats

# Show top 20 buckets
s3-insight stats --top 20

# Use specific AWS profile
s3-insight stats --profile dev
```

## Usage Examples

### Complete Workflow

```bash
# 1. Collect inventory data
s3-insight inventory --profile production --output inventory.jsonl

# 2. Generate comprehensive reports
s3-insight report --input inventory.jsonl --upload --output-dir reports

# 3. Generate dashboard overview
s3-insight dashboard --input inventory.jsonl --output-dir reports

# 4. View quick stats
s3-insight stats --input inventory.jsonl --top 10
```

### Troubleshooting

**File Location Issues**: If you get "No such file or directory" errors, remember that by default:
- Inventory files are saved to your home directory (`~/inventory.jsonl`)
- Reports are saved to your home directory (`~/reports/`)
- Run commands from your home directory or specify full paths

**Example**:
```bash
# If you're in the project directory, use full paths:
s3-insight report --input ~/inventory.jsonl --output-dir ~/reports

# Or change to home directory first:
cd ~
s3-insight report
```

### Large Account Analysis

```bash
# For accounts with many large buckets, use sampling
s3-insight inventory --sample 100000 --verbose

# Generate reports with focus on storage optimization
s3-insight report --top-extensions 20
```

### Development/Testing

```bash
# Use development profile
s3-insight inventory --profile dev

# Generate reports without uploading
s3-insight report --output-dir test-reports
```

## Output Files

### Inventory Data
- `inventory.jsonl`: Raw inventory data in JSONL format

### Reports
- `report-buckets.csv`: Per-bucket metrics in CSV format
- `report-account.json`: Account-level summary in JSON format
- `report.md`: Comprehensive Markdown report with charts

### Charts
- `filetype_pie.png`: File type distribution pie chart
- `storageclass_bar.png`: Storage class distribution bar chart
- `top_buckets_bar.png`: Top buckets by size horizontal bar chart
- `age_distribution_pie.png`: Object age distribution pie chart
- `region_distribution_pie.png`: Bucket distribution by region
- `comprehensive_dashboard.png`: All charts combined in a single dashboard view

## Report Contents

### Per-Bucket Metrics
- Object count and total size
- Average object size
- Storage class breakdown
- File extension distribution
- Object age analysis (recent vs. old)
- Region information

### Account-Level Summary
- Total buckets, objects, and storage
- Storage class cost analysis
- Top file extensions by count and size
- Regional distribution
- Age distribution patterns

### Visual Analytics
- Interactive pie charts for distributions
- Bar charts for comparisons
- Color-coded visualizations
- Professional styling and formatting

## AWS Permissions

The following AWS permissions are required:

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "s3:ListAllMyBuckets",
                "s3:ListBucket",
                "s3:GetBucketLocation",
                "s3:GetObject",
                "s3:PutObject",
                "s3:CreateBucket",
                "s3:PutBucketPolicy",
                "s3:PutBucketWebsite"
            ],
            "Resource": [
                "arn:aws:s3:::*",
                "arn:aws:s3:::*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": "sts:GetCallerIdentity",
            "Resource": "*"
        }
    ]
}
```

## Configuration

### AWS Profiles

S3-Insight supports AWS profiles for different environments:

```bash
# Use specific profile
s3-insight inventory --profile production

# Use default profile
s3-insight inventory
```

### Sampling Configuration

For large buckets (>100M objects), S3-Insight automatically samples objects:

```bash
# Default sample size (100,000 objects)
s3-insight inventory

# Custom sample size
s3-insight inventory --sample 50000

# Disable sampling (not recommended for large buckets)
s3-insight inventory --sample 0
```

## S3 Reports Bucket

When using the `--upload` flag, S3-Insight creates a dedicated reports bucket:

- **Bucket Name**: `s3-insight-reports-<account-id>`
- **Location**: us-east-1 (default)
- **Access**: Public read access for reports
- **Website**: Static website hosting enabled
- **Structure**: Organized by timestamp and file type

### Reports Bucket Structure

```
s3-insight-reports-123456789012/
├── reports/
│   └── 20241201_143022/
│       ├── report-buckets.csv
│       ├── report-account.json
│       └── report.md
├── charts/
│   └── 20241201_143022/
│       ├── filetype_pie.png
│       ├── storageclass_bar.png
│       └── ...
└── index.html
```