"""Chart generation module for S3 inventory data."""

import os
from typing import Any, Dict, List, Tuple

import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure


class ChartGenerator:
    """Generates charts from S3 inventory data."""
    
    def __init__(self, output_dir: str = "charts", dpi: int = 300) -> None:
        """Initialize the chart generator.
        
        Args:
            output_dir: Directory to save charts
            dpi: DPI for chart images
        """
        self.output_dir = output_dir
        self.dpi = dpi
        os.makedirs(output_dir, exist_ok=True)
        
        # Set matplotlib style
        plt.style.use('default')
        plt.rcParams['figure.figsize'] = (12, 8)
        plt.rcParams['font.size'] = 10
        plt.rcParams['axes.titlesize'] = 14
        plt.rcParams['axes.labelsize'] = 12
    
    def generate_charts(
        self,
        bucket_metrics: Dict[str, Any],
        account_metrics: Dict[str, Any],
        top_extensions: int = 10
    ) -> Dict[str, str]:
        """Generate all charts from inventory data.
        
        Args:
            bucket_metrics: Per-bucket metrics
            account_metrics: Account-level metrics
            top_extensions: Number of top extensions to show
            
        Returns:
            Dictionary mapping chart names to file paths
        """
        charts = {}
        
        # File type distribution pie chart
        if account_metrics["file_extensions"]:
            charts["filetype_pie"] = self._create_filetype_pie_chart(
                account_metrics["file_extensions"], top_extensions
            )
        
        # Storage class distribution bar chart
        if account_metrics["storage_classes"]:
            charts["storageclass_bar"] = self._create_storage_class_bar_chart(
                account_metrics["storage_classes"]
            )
        
        # Top buckets by size bar chart
        if bucket_metrics:
            charts["top_buckets_bar"] = self._create_top_buckets_chart(bucket_metrics)
        
        # Age distribution pie chart
        if account_metrics["age_buckets"]["recent"] > 0 or account_metrics["age_buckets"]["old"] > 0:
            charts["age_distribution_pie"] = self._create_age_distribution_chart(
                account_metrics["age_buckets"]
            )
        
        # Region distribution pie chart
        if account_metrics["regions"]:
            charts["region_distribution_pie"] = self._create_region_distribution_chart(
                account_metrics["regions"]
            )
        
        return charts
    
    def _create_filetype_pie_chart(self, file_extensions: Dict[str, Any], top_n: int) -> str:
        """Create pie chart for file type distribution.
        
        Args:
            file_extensions: File extension data
            top_n: Number of top extensions to show
            
        Returns:
            Path to saved chart file
        """
        # Get top N extensions by count
        sorted_exts = sorted(
            file_extensions.items(),
            key=lambda x: x[1]["count"],
            reverse=True
        )[:top_n]
        
        # Prepare data
        labels = []
        sizes = []
        colors = plt.cm.Set3(range(len(sorted_exts)))
        
        for ext, data in sorted_exts:
            label = ext if ext != "no-extension" else "No Extension"
            labels.append(label)
            sizes.append(data["count"])
        
        # Create chart
        fig, ax = plt.subplots(figsize=(12, 8))
        
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            textprops={'fontsize': 10}
        )
        
        # Enhance text appearance
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title('File Type Distribution (by Object Count)', fontsize=16, fontweight='bold', pad=20)
        
        # Add legend
        legend_elements = [
            mpatches.Patch(color=colors[i], label=f"{labels[i]}: {sizes[i]:,} objects")
            for i in range(len(labels))
        ]
        ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
        
        plt.tight_layout()
        
        # Save chart
        filename = os.path.join(self.output_dir, "filetype_pie.png")
        plt.savefig(filename, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def _create_storage_class_bar_chart(self, storage_classes: Dict[str, Any]) -> str:
        """Create bar chart for storage class distribution.
        
        Args:
            storage_classes: Storage class data
            
        Returns:
            Path to saved chart file
        """
        # Prepare data
        classes = list(storage_classes.keys())
        counts = [storage_classes[cls]["count"] for cls in classes]
        sizes_gb = [storage_classes[cls]["size_gb"] for cls in classes]
        
        # Create subplots
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 10))
        
        # Object count chart
        bars1 = ax1.bar(classes, counts, color=plt.cm.viridis(range(len(classes))))
        ax1.set_title('Storage Class Distribution (by Object Count)', fontsize=14, fontweight='bold')
        ax1.set_ylabel('Number of Objects')
        ax1.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, count in zip(bars1, counts):
            height = bar.get_height()
            ax1.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{count:,}', ha='center', va='bottom', fontweight='bold')
        
        # Size chart
        bars2 = ax2.bar(classes, sizes_gb, color=plt.cm.plasma(range(len(classes))))
        ax2.set_title('Storage Class Distribution (by Size)', fontsize=14, fontweight='bold')
        ax2.set_ylabel('Size (GB)')
        ax2.tick_params(axis='x', rotation=45)
        
        # Add value labels on bars
        for bar, size in zip(bars2, sizes_gb):
            height = bar.get_height()
            ax2.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                    f'{size:.1f} GB', ha='center', va='bottom', fontweight='bold')
        
        plt.tight_layout()
        
        # Save chart
        filename = os.path.join(self.output_dir, "storageclass_bar.png")
        plt.savefig(filename, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def _create_top_buckets_chart(self, bucket_metrics: Dict[str, Any], top_n: int = 10) -> str:
        """Create bar chart for top buckets by size.
        
        Args:
            bucket_metrics: Per-bucket metrics
            top_n: Number of top buckets to show
            
        Returns:
            Path to saved chart file
        """
        # Get top buckets by size
        sorted_buckets = sorted(
            bucket_metrics.items(),
            key=lambda x: x[1]["total_size_gb"],
            reverse=True
        )[:top_n]
        
        bucket_names = [name for name, _ in sorted_buckets]
        sizes_gb = [metrics["total_size_gb"] for _, metrics in sorted_buckets]
        
        # Create chart
        fig, ax = plt.subplots(figsize=(14, 8))
        
        bars = ax.barh(bucket_names, sizes_gb, color=plt.cm.coolwarm(range(len(bucket_names))))
        ax.set_title(f'Top {top_n} Buckets by Size', fontsize=16, fontweight='bold')
        ax.set_xlabel('Size (GB)')
        
        # Add value labels on bars
        for bar, size in zip(bars, sizes_gb):
            width = bar.get_width()
            ax.text(width + width*0.01, bar.get_y() + bar.get_height()/2,
                   f'{size:.1f} GB', ha='left', va='center', fontweight='bold')
        
        # Invert y-axis to show largest at top
        ax.invert_yaxis()
        
        plt.tight_layout()
        
        # Save chart
        filename = os.path.join(self.output_dir, "top_buckets_bar.png")
        plt.savefig(filename, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def _create_age_distribution_chart(self, age_buckets: Dict[str, int]) -> str:
        """Create pie chart for object age distribution.
        
        Args:
            age_buckets: Age bucket data
            
        Returns:
            Path to saved chart file
        """
        labels = ['Recent (≤30 days)', 'Old (>30 days)']
        sizes = [age_buckets["recent"], age_buckets["old"]]
        colors = ['#2ecc71', '#e74c3c']  # Green for recent, red for old
        
        # Create chart
        fig, ax = plt.subplots(figsize=(10, 8))
        
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            textprops={'fontsize': 12}
        )
        
        # Enhance text appearance
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title('Object Age Distribution', fontsize=16, fontweight='bold', pad=20)
        
        # Add legend with counts
        legend_elements = [
            mpatches.Patch(color=colors[i], label=f"{labels[i]}: {sizes[i]:,} objects")
            for i in range(len(labels))
        ]
        ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
        
        plt.tight_layout()
        
        # Save chart
        filename = os.path.join(self.output_dir, "age_distribution_pie.png")
        plt.savefig(filename, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return filename
    
    def _create_region_distribution_chart(self, regions: Dict[str, int]) -> str:
        """Create pie chart for bucket region distribution.
        
        Args:
            regions: Region data
            
        Returns:
            Path to saved chart file
        """
        labels = list(regions.keys())
        sizes = list(regions.values())
        colors = plt.cm.tab10(range(len(labels)))
        
        # Create chart
        fig, ax = plt.subplots(figsize=(10, 8))
        
        wedges, texts, autotexts = ax.pie(
            sizes,
            labels=labels,
            autopct='%1.1f%%',
            startangle=90,
            colors=colors,
            textprops={'fontsize': 10}
        )
        
        # Enhance text appearance
        for autotext in autotexts:
            autotext.set_color('white')
            autotext.set_fontweight('bold')
        
        ax.set_title('Bucket Distribution by Region', fontsize=16, fontweight='bold', pad=20)
        
        # Add legend with counts
        legend_elements = [
            mpatches.Patch(color=colors[i], label=f"{labels[i]}: {sizes[i]} buckets")
            for i in range(len(labels))
        ]
        ax.legend(handles=legend_elements, loc='center left', bbox_to_anchor=(1, 0, 0.5, 1))
        
        plt.tight_layout()
        
        # Save chart
        filename = os.path.join(self.output_dir, "region_distribution_pie.png")
        plt.savefig(filename, dpi=self.dpi, bbox_inches='tight')
        plt.close()
        
        return filename 