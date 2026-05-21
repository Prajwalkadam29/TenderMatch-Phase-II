import matplotlib
import matplotlib.pyplot as plt
import seaborn as sns

def set_academic_style():
    """Sets a consistent academic matplotlib style for all paper figures."""
    matplotlib.rcParams.update({
        'font.family': 'serif',
        'font.size': 11,
        'axes.titlesize': 13,
        'axes.labelsize': 11,
        'xtick.labelsize': 10,
        'ytick.labelsize': 10,
        'figure.dpi': 300,
        'savefig.dpi': 300,
        'savefig.bbox': 'tight',
        'savefig.format': 'pdf',
        'lines.linewidth': 1.5,
        'axes.grid': True,
        'grid.alpha': 0.3,
        'axes.edgecolor': 'black'
    })
    sns.set_theme(style="whitegrid", context="paper")
    
COLORS = {
    'primary': '#4C72B0',
    'secondary': '#DD8452',
    'success': '#55A868',
    'danger': '#C44E52',
    'warning': '#E4B431',
    'neutral': '#8C8C8C'
}
