"""S3-Insight CLI entry point."""

import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
import os

from . import __version__
from .inventory import S3Inventory
from .aggregate import S3Aggregator
from .charts import ChartGenerator
from .formats import ReportWriter
from .publish import S3Publisher
from .utils import get_aws_account_id

app = typer.Typer(
    name="s3-insight",
    help="AWS S3 bucket inventory and analytics CLI tool",
    add_completion=False,
)
console = Console()


def version_callback(value: bool) -> None:
    """Print version and exit."""
    if value:
        console.print(f"[bold blue]s3-insight[/bold blue] version [bold green]{__version__}[/bold green]")
        raise typer.Exit()


@app.callback()
def main(
    version: bool = typer.Option(
        None, "--version", callback=version_callback, is_eager=True, help="Show version and exit"
    ),
) -> None:
    """S3-Insight: Comprehensive AWS S3 bucket inventory and analytics."""
    pass


@app.command()
def inventory(
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    sample: int = typer.Option(100000, "--sample", "-s", help="Sample size for large buckets (>100M objects)"),
    output: str = typer.Option("~/inventory.jsonl", "--output", "-o", help="Output file for raw inventory data"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Verbose output"),
) -> None:
    """Collect S3 bucket inventory data with optional sampling for large buckets."""
    console.print(f"[bold green]🔍 Starting S3 inventory collection...[/bold green]")
    
    # Expand user path for output file
    output_path = os.path.expanduser(output)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing inventory collector...", total=None)
            
            inventory = S3Inventory(profile=profile, sample_size=sample, verbose=verbose)
            progress.update(task, description="Discovering S3 buckets...")
            
            buckets = inventory.discover_buckets()
            progress.update(task, description=f"Found {len(buckets)} buckets")
            
            progress.update(task, description="Collecting object inventory...")
            inventory_data = inventory.collect_inventory(buckets)
            
            progress.update(task, description="Writing inventory data...")
            inventory.write_inventory(inventory_data, output_path)
        
        console.print(f"[bold green]✅ Inventory collection complete![/bold green]")
        console.print(f"📊 Data written to: [bold blue]{output_path}[/bold blue]")
        
        # Summary stats
        total_objects = sum(bucket["object_count"] for bucket in inventory_data.values())
        total_size = sum(bucket["total_size"] for bucket in inventory_data.values())
        
        summary_table = Table(title="Inventory Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="magenta")
        
        summary_table.add_row("Buckets", str(len(buckets)))
        summary_table.add_row("Total Objects", f"{total_objects:,}")
        summary_table.add_row("Total Size", f"{total_size / (1024**3):.2f} GB")
        
        console.print(summary_table)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error during inventory collection: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def report(
    inventory_file: str = typer.Option("~/inventory.jsonl", "--input", "-i", help="Input inventory file"),
    upload: bool = typer.Option(False, "--upload", "-u", help="Upload reports to S3"),
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
    output_dir: str = typer.Option("~/reports", "--output-dir", "-o", help="Output directory for reports"),
    top_extensions: int = typer.Option(10, "--top-extensions", "-t", help="Number of top extensions to show"),
) -> None:
    """Generate comprehensive reports and charts from inventory data."""
    console.print(f"[bold green]📊 Generating S3 insight reports...[/bold green]")
    
    # Expand user paths
    inventory_path = os.path.expanduser(inventory_file)
    output_path = os.path.expanduser(output_dir)
    
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Loading inventory data...", total=None)
            
            # Load and aggregate data
            inventory = S3Inventory()
            inventory_data = inventory.load_inventory(inventory_path)
            
            progress.update(task, description="Aggregating metrics...")
            aggregator = S3Aggregator()
            bucket_metrics = aggregator.aggregate_buckets(inventory_data)
            account_metrics = aggregator.aggregate_account(bucket_metrics)
            
            progress.update(task, description="Generating charts...")
            chart_gen = ChartGenerator(output_dir=os.path.join(output_path, "charts"))
            charts = chart_gen.generate_charts(bucket_metrics, account_metrics, top_extensions)
            
            progress.update(task, description="Writing reports...")
            writer = ReportWriter()
            report_files = writer.write_reports(
                bucket_metrics, account_metrics, charts, output_path
            )
            
            if upload:
                progress.update(task, description="Uploading to S3...")
                publisher = S3Publisher(profile=profile)
                upload_urls = publisher.publish_reports(report_files)
        
        console.print(f"[bold green]✅ Report generation complete![/bold green]")
        console.print(f"📁 Reports saved to: [bold blue]{output_path}[/bold blue]")
        
        if upload:
            console.print(f"🌐 Reports uploaded to S3")
            for url in upload_urls:
                console.print(f"   📄 {url}")
        
        # Quick summary
        summary_table = Table(title="Report Summary")
        summary_table.add_column("Report Type", style="cyan")
        summary_table.add_column("File", style="magenta")
        
        for report_type, filepath in report_files.items():
            summary_table.add_row(report_type, filepath)
        
        console.print(summary_table)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error during report generation: {e}[/bold red]")
        raise typer.Exit(1)


@app.command()
def stats(
    inventory_file: str = typer.Option("~/inventory.jsonl", "--input", "-i", help="Input inventory file"),
    top: int = typer.Option(10, "--top", "-t", help="Number of top buckets to show"),
    profile: str = typer.Option(None, "--profile", "-p", help="AWS profile to use"),
) -> None:
    """Display quick statistics from inventory data."""
    console.print(f"[bold green]📈 S3 Statistics Overview[/bold green]")
    
    # Expand user path
    inventory_path = os.path.expanduser(inventory_file)
    
    try:
        # Load and aggregate data
        inventory = S3Inventory()
        inventory_data = inventory.load_inventory(inventory_path)
        
        aggregator = S3Aggregator()
        bucket_metrics = aggregator.aggregate_buckets(inventory_data)
        account_metrics = aggregator.aggregate_account(bucket_metrics)
        
        # Account overview
        account_id = get_aws_account_id(profile)
        console.print(f"\n[bold cyan]Account: {account_id}[/bold cyan]")
        
        # Account summary table
        account_table = Table(title="Account Summary")
        account_table.add_column("Metric", style="cyan")
        account_table.add_column("Value", style="magenta")
        
        account_table.add_row("Total Buckets", str(account_metrics["bucket_count"]))
        account_table.add_row("Total Objects", f"{account_metrics['total_objects']:,}")
        account_table.add_row("Total Size", f"{account_metrics['total_size_gb']:.2f} GB")
        account_table.add_row("Avg Object Size", f"{account_metrics['avg_object_size_kb']:.2f} KB")
        
        console.print(account_table)
        
        # Top buckets by size
        top_buckets_table = Table(title=f"Top {top} Buckets by Size")
        top_buckets_table.add_column("Rank", style="cyan")
        top_buckets_table.add_column("Bucket", style="blue")
        top_buckets_table.add_column("Objects", style="green")
        top_buckets_table.add_column("Size (GB)", style="yellow")
        top_buckets_table.add_column("Avg Size (KB)", style="magenta")
        
        sorted_buckets = sorted(
            bucket_metrics.items(),
            key=lambda x: x[1]["total_size"],
            reverse=True
        )[:top]
        
        for i, (bucket_name, metrics) in enumerate(sorted_buckets, 1):
            top_buckets_table.add_row(
                str(i),
                bucket_name,
                f"{metrics['object_count']:,}",
                f"{metrics['total_size_gb']:.2f}",
                f"{metrics['avg_object_size_kb']:.2f}"
            )
        
        console.print(top_buckets_table)
        
        # Top file extensions
        if account_metrics["file_extensions"]:
            ext_table = Table(title=f"Top {top} File Extensions")
            ext_table.add_column("Extension", style="cyan")
            ext_table.add_column("Objects", style="green")
            ext_table.add_column("Size (GB)", style="yellow")
            ext_table.add_column("% Objects", style="blue")
            ext_table.add_column("% Size", style="magenta")
            
            sorted_exts = sorted(
                account_metrics["file_extensions"].items(),
                key=lambda x: x[1]["count"],
                reverse=True
            )[:top]
            
            total_objects = account_metrics["total_objects"]
            total_size = account_metrics["total_size"]
            
            for ext, data in sorted_exts:
                ext_table.add_row(
                    ext or "no-extension",
                    f"{data['count']:,}",
                    f"{data['size_gb']:.2f}",
                    f"{data['count'] / total_objects * 100:.1f}%",
                    f"{data['size'] / total_size * 100:.1f}%"
                )
            
            console.print(ext_table)
        
    except Exception as e:
        console.print(f"[bold red]❌ Error displaying statistics: {e}[/bold red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    app() 