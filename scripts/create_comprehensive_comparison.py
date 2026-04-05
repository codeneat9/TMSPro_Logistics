"""
Create comprehensive model comparison table with multiple evaluation metrics
"""

import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from pathlib import Path
import numpy as np

# Set style
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# Load comparison results
models_dir = Path(__file__).parent.parent / 'models'
df = pd.read_csv(models_dir / 'model_comparison.csv')

print("="*80)
print("📊 COMPREHENSIVE MODEL COMPARISON - ALL METRICS")
print("="*80)

# Display full comparison
print("\n" + df.to_string(index=False))

# Create comprehensive visualization
fig, ax = plt.subplots(figsize=(16, 8))

# Prepare data for heatmap
metrics_to_show = ['Accuracy', 'Precision', 'Recall', 'F1 Score', 'ROC-AUC']
heatmap_data = df[metrics_to_show].T

# Create heatmap
im = ax.imshow(heatmap_data, cmap='RdYlGn', aspect='auto', vmin=0, vmax=1)

# Set ticks and labels
ax.set_xticks(np.arange(len(df)))
ax.set_yticks(np.arange(len(metrics_to_show)))
ax.set_xticklabels(df['Model'], fontsize=12, fontweight='bold')
ax.set_yticklabels(metrics_to_show, fontsize=12, fontweight='bold')

# Rotate x labels
plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")

# Add text annotations
for i in range(len(metrics_to_show)):
    for j in range(len(df)):
        value = heatmap_data.iloc[i, j]
        text = ax.text(j, i, f'{value:.4f}',
                      ha="center", va="center", color="black", 
                      fontsize=11, fontweight='bold')

# Add colorbar
cbar = plt.colorbar(im, ax=ax)
cbar.set_label('Score', rotation=270, labelpad=20, fontsize=12, fontweight='bold')

# Title
ax.set_title('🏆 MODEL PERFORMANCE COMPARISON - ALL METRICS\n' + 
             'Higher values = Better performance (Green), Lower values = Worse performance (Red)',
             fontsize=14, fontweight='bold', pad=20)

plt.tight_layout()
plt.savefig(models_dir / 'comprehensive_comparison_heatmap.png', dpi=300, bbox_inches='tight')
print(f"\n✅ Saved heatmap: comprehensive_comparison_heatmap.png")

# Create detailed table visualization
fig, ax = plt.subplots(figsize=(18, 6))
ax.axis('tight')
ax.axis('off')

# Prepare table data
table_data = []
for _, row in df.iterrows():
    table_data.append([
        row['Model'],
        f"{row['Accuracy']:.4f}\n({row['Accuracy']*100:.2f}%)",
        f"{row['Precision']:.4f}",
        f"{row['Recall']:.4f}",
        f"{row['F1 Score']:.4f}",
        f"{row['ROC-AUC']:.4f}",
        f"{row['Training Time (s)']:.1f}s"
    ])

# Column headers
headers = ['Model', 'Accuracy', 'Precision', 'Recall', 'F1 Score', 'ROC-AUC', 'Training Time']

# Create table
table = ax.table(cellText=table_data, colLabels=headers,
                cellLoc='center', loc='center',
                colWidths=[0.18, 0.14, 0.12, 0.12, 0.12, 0.12, 0.14])

# Style the table
table.auto_set_font_size(False)
table.set_fontsize(11)
table.scale(1, 2.5)

# Color header
for i in range(len(headers)):
    cell = table[(0, i)]
    cell.set_facecolor('#4CAF50')
    cell.set_text_props(weight='bold', color='white', fontsize=12)

# Color best values in each column
for col_idx in range(1, len(headers)):
    if col_idx == 6:  # Training time - lower is better
        best_idx = df.iloc[:, col_idx].idxmin() + 1
        cell = table[(best_idx, col_idx)]
        cell.set_facecolor('#FFD700')
        cell.set_text_props(weight='bold')
    else:  # Other metrics - higher is better
        best_idx = df.iloc[:, col_idx].idxmax() + 1
        cell = table[(best_idx, col_idx)]
        cell.set_facecolor('#FFD700')
        cell.set_text_props(weight='bold')

# Alternate row colors
for i in range(1, len(table_data) + 1):
    for j in range(len(headers)):
        cell = table[(i, j)]
        if i % 2 == 0:
            cell.set_facecolor('#f0f0f0')
        else:
            cell.set_facecolor('#ffffff')

plt.title('📊 DETAILED MODEL COMPARISON TABLE\n' + 
          'Gold highlighting = Best performance in each metric',
          fontsize=14, fontweight='bold', pad=20)

plt.savefig(models_dir / 'comprehensive_comparison_table.png', dpi=300, bbox_inches='tight')
print(f"✅ Saved table: comprehensive_comparison_table.png")

# Create bar chart comparison
fig, axes = plt.subplots(2, 3, figsize=(18, 10))
axes = axes.flatten()

metrics = ['Accuracy', 'Precision', 'Recall', 'F1 Score', 'ROC-AUC', 'Training Time (s)']
colors = plt.cm.Set3(range(len(df)))

for idx, metric in enumerate(metrics):
    ax = axes[idx]
    
    if metric == 'Training Time (s)':
        # Lower is better for training time
        bars = ax.barh(df['Model'], df[metric], color=colors)
        ax.set_xlabel('Time (seconds)', fontweight='bold')
        best_idx = df[metric].idxmin()
    else:
        # Higher is better for other metrics
        bars = ax.barh(df['Model'], df[metric], color=colors)
        ax.set_xlabel('Score', fontweight='bold')
        best_idx = df[metric].idxmax()
    
    # Highlight best performer
    bars[best_idx].set_color('#FFD700')
    bars[best_idx].set_edgecolor('red')
    bars[best_idx].set_linewidth(3)
    
    ax.set_title(f'{metric}', fontsize=12, fontweight='bold')
    ax.set_ylabel('Model', fontweight='bold')
    ax.grid(axis='x', alpha=0.3)
    
    # Add value labels
    for i, (bar, value) in enumerate(zip(bars, df[metric])):
        if metric == 'Training Time (s)':
            label = f'{value:.1f}s'
        else:
            label = f'{value:.4f}'
        ax.text(value, bar.get_y() + bar.get_height()/2, f'  {label}',
               va='center', fontweight='bold' if i == best_idx else 'normal',
               fontsize=10)

plt.suptitle('🏆 MODEL PERFORMANCE COMPARISON - ALL METRICS\n' +
             'Gold bars with red border = Best performance',
             fontsize=16, fontweight='bold', y=0.995)
plt.tight_layout(rect=[0, 0, 1, 0.98])
plt.savefig(models_dir / 'comprehensive_comparison_bars.png', dpi=300, bbox_inches='tight')
print(f"✅ Saved bar charts: comprehensive_comparison_bars.png")

# Print summary
print("\n" + "="*80)
print("🏆 BEST PERFORMERS BY METRIC")
print("="*80)
for metric in metrics:
    if metric == 'Training Time (s)':
        best_idx = df[metric].idxmin()
        best_model = df.loc[best_idx, 'Model']
        best_value = df.loc[best_idx, metric]
        print(f"  {metric:20s}: {best_model:20s} ({best_value:.1f}s)")
    else:
        best_idx = df[metric].idxmax()
        best_model = df.loc[best_idx, 'Model']
        best_value = df.loc[best_idx, metric]
        print(f"  {metric:20s}: {best_model:20s} ({best_value:.4f})")

# Overall recommendation
print("\n" + "="*80)
print("💡 RECOMMENDATION")
print("="*80)
best_f1_idx = df['F1 Score'].idxmax()
best_model = df.loc[best_f1_idx, 'Model']
print(f"\n  🥇 BEST MODEL: {best_model}")
print(f"     - F1 Score: {df.loc[best_f1_idx, 'F1 Score']:.4f} (Best balance of Precision & Recall)")
print(f"     - ROC-AUC: {df.loc[best_f1_idx, 'ROC-AUC']:.4f}")
print(f"     - Accuracy: {df.loc[best_f1_idx, 'Accuracy']:.4f} ({df.loc[best_f1_idx, 'Accuracy']*100:.2f}%)")
print(f"     - Recall: {df.loc[best_f1_idx, 'Recall']:.4f} (Catches {df.loc[best_f1_idx, 'Recall']*100:.1f}% of delays)")
print(f"     - Training Time: {df.loc[best_f1_idx, 'Training Time (s)']:.1f}s")

print("\n" + "="*80)
print("✅ COMPREHENSIVE COMPARISON COMPLETE!")
print("="*80)
print("\n📁 Generated Files:")
print("  1. comprehensive_comparison_heatmap.png - Color-coded metric heatmap")
print("  2. comprehensive_comparison_table.png - Detailed comparison table")
print("  3. comprehensive_comparison_bars.png - Bar chart for each metric")
