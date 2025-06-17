# S3-Insight

A comprehensive Python CLI tool for AWS S3 bucket inventory and analytics. S3-Insight provides detailed insights into your S3 storage usage, including object counts, file type distributions, storage class breakdowns, and cost analysis.

## Features

- **🔍 Complete S3 Inventory**: Discover and analyze all S3 buckets in your AWS account
- **📊 Rich Analytics**: Object counts, total bytes, average object sizes, file type distributions
- **🎯 Smart Sampling**: Automatic sampling for large buckets (>100M objects) to improve performance
- **📈 Visual Charts**: Auto-generated pie charts and bar charts using Matplotlib
- **📋 Multiple Formats**: Export reports in CSV, JSON, and Markdown formats
- **☁️ S3 Publishing**: Automatically upload reports to a dedicated S3 reports bucket
- **💰 Cost Analysis**: Storage class breakdown and cost estimation
- **⏰ Age Analysis**: Object age distribution (recent vs. old objects)
- **🌍 Regional Insights**: Bucket distribution across AWS regions

## Installation

### Prerequisites

- Python 3.10 or higher
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

### 1. Collect S3 Inventory

```bash
# Basic inventory collection
s3-insight inventory

# With specific AWS profile
s3-insight inventory --profile prod

# Custom sample size for large buckets
s3-insight inventory --sample 50000

# Verbose output
s3-insight inventory --verbose
```

### 2. Generate Reports and Charts

```bash
# Generate all reports and charts
s3-insight report

# Upload reports to S3
s3-insight report --upload

# Custom output directory
s3-insight report --output-dir my-reports

# Specify number of top extensions to show
s3-insight report --top-extensions 15
```

### 3. View Quick Statistics

```bash
# Display account overview
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

# 3. View quick stats
s3-insight stats --input inventory.jsonl --top 10
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

## Development

### Project Structure

```
s3-insight/
├── src/s3_insight/
│   ├── cli.py          # CLI entry point
│   ├── inventory.py    # S3 inventory collection
│   ├── aggregate.py    # Data aggregation and metrics
│   ├── charts.py       # Chart generation
│   ├── formats.py      # Report format writers
│   ├── publish.py      # S3 upload functionality
│   └── utils.py        # Utility functions
├── tests/              # Test suite
├── docs/               # Documentation
└── pyproject.toml      # Project configuration
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=s3_insight

# Run specific test file
pytest tests/test_inventory.py
```

### Code Quality

```bash
# Format code
black src/ tests/

# Sort imports
isort src/ tests/

# Type checking
mypy src/

# Linting
flake8 src/ tests/
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Ensure all tests pass
6. Submit a pull request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Support

- **Issues**: [GitHub Issues](https://github.com/your-org/s3-insight/issues)
- **Documentation**: [Wiki](https://github.com/your-org/s3-insight/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/s3-insight/discussions)

## Roadmap

- [ ] Scheduled inventory collection via GitHub Actions
- [ ] Cost optimization recommendations
- [ ] Lifecycle policy analysis
- [ ] Cross-account inventory support
- [ ] Real-time monitoring dashboard
- [ ] Integration with AWS Cost Explorer
- [ ] Support for S3 Inventory reports
- [ ] Advanced filtering and querying
- [ ] Export to additional formats (Excel, PDF)
- [ ] Custom chart templates

## Acknowledgments

- Built with [Typer](https://typer.tiangolo.com/) for CLI
- Charts generated with [Matplotlib](https://matplotlib.org/)
- Rich console output with [Rich](https://rich.readthedocs.io/)
- AWS integration via [boto3](https://boto3.amazonaws.com/) 