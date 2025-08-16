"""
CSV Dashboard Generator for MCP

AI-powered CSV analysis and dashboard generation that creates beautiful, 
interactive dashboards from any CSV file with intelligent chart selection,
statistical insights, and responsive design.
"""

import csv
import io
import json
import logging
import pandas as pd
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
import base64
import statistics

logger = logging.getLogger(__name__)


class CSVDashboardGenerator:
    """Generates beautiful, interactive dashboards from CSV files."""
    
    def __init__(self):
        """Initialize the CSV dashboard generator."""
        self.supported_chart_types = {
            'line': 'Line Chart - Perfect for time series and trends',
            'bar': 'Bar Chart - Great for categorical comparisons',
            'pie': 'Pie Chart - Ideal for proportions and percentages',
            'scatter': 'Scatter Plot - Shows correlations between variables',
            'histogram': 'Histogram - Displays data distribution',
            'area': 'Area Chart - Emphasizes magnitude of change',
            'donut': 'Donut Chart - Modern alternative to pie charts',
            'heatmap': 'Heatmap - Perfect for correlation matrices'
        }
        
    async def analyze_csv_structure(self, csv_content: str) -> Dict[str, Any]:
        """Analyze CSV structure and return comprehensive metadata."""
        try:
            # Read CSV into pandas DataFrame
            csv_buffer = io.StringIO(csv_content)
            df = pd.read_csv(csv_buffer)
            
            # Basic information
            analysis = {
                'total_rows': len(df),
                'total_columns': len(df.columns),
                'columns': list(df.columns),
                'data_types': {},
                'missing_values': {},
                'sample_data': {},
                'statistics': {},
                'column_analysis': {},
                'recommended_charts': [],
                'data_quality_score': 0
            }
            
            # Analyze each column
            quality_scores = []
            
            for column in df.columns:
                col_data = df[column]
                
                # Data type detection
                if pd.api.types.is_numeric_dtype(col_data):
                    dtype = 'numeric'
                elif pd.api.types.is_datetime64_any_dtype(col_data):
                    dtype = 'datetime'
                elif col_data.nunique() / len(col_data) < 0.5:  # Less than 50% unique values
                    dtype = 'categorical'
                else:
                    dtype = 'text'
                
                analysis['data_types'][column] = dtype
                
                # Missing values
                missing_count = col_data.isnull().sum()
                analysis['missing_values'][column] = {
                    'count': int(missing_count),
                    'percentage': float(missing_count / len(col_data) * 100)
                }
                
                # Sample data (first 5 non-null values)
                sample_values = col_data.dropna().head(5).tolist()
                analysis['sample_data'][column] = sample_values
                
                # Column-specific analysis
                col_analysis = {
                    'unique_values': int(col_data.nunique()),
                    'most_frequent': None,
                    'data_quality_score': 0
                }
                
                if dtype == 'numeric':
                    # Statistical analysis for numeric columns
                    analysis['statistics'][column] = {
                        'mean': float(col_data.mean()) if not col_data.empty else 0,
                        'median': float(col_data.median()) if not col_data.empty else 0,
                        'std': float(col_data.std()) if not col_data.empty else 0,
                        'min': float(col_data.min()) if not col_data.empty else 0,
                        'max': float(col_data.max()) if not col_data.empty else 0,
                        'quartiles': {
                            'q25': float(col_data.quantile(0.25)) if not col_data.empty else 0,
                            'q75': float(col_data.quantile(0.75)) if not col_data.empty else 0
                        }
                    }
                    col_analysis['data_quality_score'] = max(0, 100 - analysis['missing_values'][column]['percentage'])
                
                elif dtype == 'categorical':
                    # Frequency analysis for categorical columns
                    value_counts = col_data.value_counts()
                    col_analysis['most_frequent'] = str(value_counts.index[0]) if not value_counts.empty else None
                    col_analysis['frequency_distribution'] = {
                        str(k): int(v) for k, v in value_counts.head(10).items()
                    }
                    col_analysis['data_quality_score'] = max(0, 100 - analysis['missing_values'][column]['percentage'])
                
                else:
                    # Text analysis
                    col_analysis['data_quality_score'] = max(0, 100 - analysis['missing_values'][column]['percentage'])
                
                analysis['column_analysis'][column] = col_analysis
                quality_scores.append(col_analysis['data_quality_score'])
            
            # Overall data quality score
            analysis['data_quality_score'] = sum(quality_scores) / len(quality_scores) if quality_scores else 0
            
            # Recommend charts based on data structure
            analysis['recommended_charts'] = self._recommend_charts(df, analysis)
            
            logger.info(f"CSV analysis complete: {analysis['total_rows']} rows, {analysis['total_columns']} columns")
            return analysis
            
        except Exception as e:
            logger.error(f"Failed to analyze CSV: {e}")
            raise ValueError(f"CSV analysis failed: {str(e)}")
    
    def _recommend_charts(self, df: pd.DataFrame, analysis: Dict) -> List[Dict]:
        """Intelligently recommend chart types based on data characteristics."""
        recommendations = []
        
        numeric_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'numeric']
        categorical_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'categorical']
        datetime_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'datetime']
        
        # Time series recommendations
        if datetime_cols and numeric_cols:
            recommendations.append({
                'chart_type': 'line',
                'title': 'Time Series Analysis',
                'x_axis': datetime_cols[0],
                'y_axis': numeric_cols[0],
                'description': 'Track changes over time',
                'priority': 'high'
            })
        
        # Categorical vs Numeric recommendations
        if categorical_cols and numeric_cols:
            recommendations.append({
                'chart_type': 'bar',
                'title': 'Category Comparison',
                'x_axis': categorical_cols[0],
                'y_axis': numeric_cols[0],
                'description': 'Compare values across categories',
                'priority': 'high'
            })
        
        # Distribution analysis for numeric columns
        if numeric_cols:
            recommendations.append({
                'chart_type': 'histogram',
                'title': 'Data Distribution',
                'x_axis': numeric_cols[0],
                'y_axis': 'frequency',
                'description': 'Understand data distribution patterns',
                'priority': 'medium'
            })
        
        # Correlation analysis for multiple numeric columns
        if len(numeric_cols) >= 2:
            recommendations.append({
                'chart_type': 'scatter',
                'title': 'Correlation Analysis',
                'x_axis': numeric_cols[0],
                'y_axis': numeric_cols[1],
                'description': 'Discover relationships between variables',
                'priority': 'medium'
            })
            
            recommendations.append({
                'chart_type': 'heatmap',
                'title': 'Correlation Matrix',
                'description': 'Visual correlation matrix of all numeric variables',
                'priority': 'medium'
            })
        
        # Proportion analysis for categorical data
        if categorical_cols:
            col_name = categorical_cols[0]
            unique_count = analysis['column_analysis'][col_name]['unique_values']
            
            if unique_count <= 10:  # Good for pie charts
                recommendations.append({
                    'chart_type': 'pie',
                    'title': f'{col_name} Distribution',
                    'x_axis': col_name,
                    'description': f'Proportional breakdown of {col_name}',
                    'priority': 'medium'
                })
        
        return recommendations
    
    async def generate_dashboard_html(
        self, 
        csv_content: str, 
        analysis: Dict[str, Any],
        dashboard_title: str = "CSV Data Dashboard",
        theme: str = "modern"
    ) -> str:
        """Generate a complete, interactive HTML dashboard."""
        
        try:
            # Read CSV data for charts
            csv_buffer = io.StringIO(csv_content)
            df = pd.read_csv(csv_buffer)
            
            # Convert DataFrame to JSON for JavaScript
            chart_data = {}
            
            # Prepare data for different chart types
            numeric_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'numeric']
            categorical_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'categorical']
            
            # Sample data for charts (limit to 1000 rows for performance)
            df_sample = df.head(1000) if len(df) > 1000 else df
            
            for col in df_sample.columns:
                if analysis['data_types'][col] == 'numeric':
                    chart_data[col] = df_sample[col].fillna(0).tolist()
                elif analysis['data_types'][col] == 'categorical':
                    value_counts = df_sample[col].value_counts().head(20)  # Top 20 categories
                    chart_data[col] = {
                        'labels': value_counts.index.tolist(),
                        'values': value_counts.values.tolist()
                    }
            
            # Generate insights
            insights = self._generate_insights(analysis, df)
            
            # Create the HTML dashboard
            dashboard_html = self._create_html_template(
                dashboard_title=dashboard_title,
                analysis=analysis,
                chart_data=chart_data,
                insights=insights,
                theme=theme
            )
            
            logger.info(f"Generated interactive dashboard: {len(dashboard_html)} characters")
            return dashboard_html
            
        except Exception as e:
            logger.error(f"Failed to generate dashboard HTML: {e}")
            raise ValueError(f"Dashboard generation failed: {str(e)}")
    
    def _generate_insights(self, analysis: Dict[str, Any], df: pd.DataFrame) -> List[Dict]:
        """Generate AI-powered insights from the data analysis."""
        insights = []
        
        # Data quality insight
        quality_score = analysis['data_quality_score']
        if quality_score >= 90:
            quality_message = "Excellent data quality! ✅"
            quality_color = "success"
        elif quality_score >= 70:
            quality_message = "Good data quality with minor issues 👍"
            quality_color = "warning"
        else:
            quality_message = "Data quality needs attention ⚠️"
            quality_color = "danger"
        
        insights.append({
            'title': 'Data Quality Score',
            'value': f"{quality_score:.1f}%",
            'message': quality_message,
            'color': quality_color,
            'icon': 'fas fa-chart-line'
        })
        
        # Dataset size insight
        total_rows = analysis['total_rows']
        size_message = ""
        if total_rows > 100000:
            size_message = "Large dataset - excellent for statistical analysis! 📊"
        elif total_rows > 10000:
            size_message = "Medium dataset - good sample size for insights 📈"
        else:
            size_message = "Small dataset - consider collecting more data 📉"
        
        insights.append({
            'title': 'Dataset Size',
            'value': f"{total_rows:,} rows",
            'message': size_message,
            'color': 'info',
            'icon': 'fas fa-database'
        })
        
        # Missing data insight
        missing_data = []
        for col, missing_info in analysis['missing_values'].items():
            if missing_info['percentage'] > 0:
                missing_data.append(f"{col}: {missing_info['percentage']:.1f}%")
        
        if missing_data:
            insights.append({
                'title': 'Missing Data',
                'value': f"{len(missing_data)} columns",
                'message': "Some columns have missing values - consider data cleaning",
                'color': 'warning',
                'icon': 'fas fa-exclamation-triangle',
                'details': missing_data[:5]  # Show top 5
            })
        else:
            insights.append({
                'title': 'Missing Data',
                'value': "None",
                'message': "Perfect! No missing values detected 🎉",
                'color': 'success',
                'icon': 'fas fa-check-circle'
            })
        
        # Numeric columns insight
        numeric_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'numeric']
        if numeric_cols:
            insights.append({
                'title': 'Numeric Analysis',
                'value': f"{len(numeric_cols)} columns",
                'message': "Ready for statistical analysis and forecasting 📊",
                'color': 'primary',
                'icon': 'fas fa-calculator'
            })
        
        return insights
    
    def _create_html_template(
        self, 
        dashboard_title: str, 
        analysis: Dict, 
        chart_data: Dict, 
        insights: List[Dict],
        theme: str
    ) -> str:
        """Create the complete HTML dashboard template."""
        
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{dashboard_title}</title>
    
    <!-- Bootstrap 5 CSS -->
    <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css" rel="stylesheet">
    
    <!-- Font Awesome -->
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css" rel="stylesheet">
    
    <!-- Chart.js -->
    <script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.0/dist/chart.min.js"></script>
    
    <!-- DataTables -->
    <link href="https://cdn.datatables.net/1.13.6/css/dataTables.bootstrap5.min.css" rel="stylesheet">
    
    <style>
        :root {{
            --primary-color: #2563eb;
            --secondary-color: #64748b;
            --accent-color: #f59e0b;
            --success-color: #10b981;
            --warning-color: #f59e0b;
            --danger-color: #ef4444;
            --info-color: #3b82f6;
            --dark-color: #1e293b;
            --light-color: #f8fafc;
        }}
        
        body {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            min-height: 100vh;
        }}
        
        .dashboard-container {{
            background: rgba(255, 255, 255, 0.95);
            backdrop-filter: blur(10px);
            border-radius: 20px;
            box-shadow: 0 20px 40px rgba(0,0,0,0.1);
            margin: 20px;
            padding: 30px;
            min-height: calc(100vh - 40px);
        }}
        
        .dashboard-header {{
            text-align: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid var(--primary-color);
        }}
        
        .dashboard-title {{
            font-size: 3rem;
            font-weight: 700;
            background: linear-gradient(135deg, var(--primary-color), var(--accent-color));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
            margin-bottom: 10px;
        }}
        
        .dashboard-subtitle {{
            color: var(--secondary-color);
            font-size: 1.2rem;
            font-weight: 400;
        }}
        
        .insight-card {{
            background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
            border: none;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            margin-bottom: 20px;
            overflow: hidden;
        }}
        
        .insight-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 20px 40px rgba(0,0,0,0.15);
        }}
        
        .insight-card .card-body {{
            padding: 25px;
        }}
        
        .insight-icon {{
            font-size: 2.5rem;
            margin-bottom: 15px;
        }}
        
        .insight-value {{
            font-size: 2rem;
            font-weight: 700;
            margin-bottom: 5px;
        }}
        
        .insight-title {{
            font-size: 1rem;
            font-weight: 600;
            margin-bottom: 10px;
            color: var(--dark-color);
        }}
        
        .insight-message {{
            font-size: 0.9rem;
            color: var(--secondary-color);
            margin-bottom: 10px;
        }}
        
        .chart-container {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-bottom: 30px;
            position: relative;
        }}
        
        .chart-title {{
            font-size: 1.3rem;
            font-weight: 600;
            margin-bottom: 20px;
            color: var(--dark-color);
            text-align: center;
        }}
        
        .data-table-container {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
            margin-top: 30px;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 40px;
        }}
        
        .text-primary {{ color: var(--primary-color) !important; }}
        .text-success {{ color: var(--success-color) !important; }}
        .text-warning {{ color: var(--warning-color) !important; }}
        .text-danger {{ color: var(--danger-color) !important; }}
        .text-info {{ color: var(--info-color) !important; }}
        
        .bg-primary {{ background-color: var(--primary-color) !important; }}
        .bg-success {{ background-color: var(--success-color) !important; }}
        .bg-warning {{ background-color: var(--warning-color) !important; }}
        .bg-danger {{ background-color: var(--danger-color) !important; }}
        .bg-info {{ background-color: var(--info-color) !important; }}
        
        /* Responsive design */
        @media (max-width: 768px) {{
            .dashboard-title {{
                font-size: 2rem;
            }}
            .dashboard-container {{
                margin: 10px;
                padding: 20px;
            }}
        }}
        
        /* Loading animation */
        .loading {{
            display: inline-block;
            width: 20px;
            height: 20px;
            border: 3px solid rgba(255,255,255,0.3);
            border-radius: 50%;
            border-top-color: #fff;
            animation: spin 1s ease-in-out infinite;
        }}
        
        @keyframes spin {{
            to {{ transform: rotate(360deg); }}
        }}
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {{
            width: 8px;
        }}
        
        ::-webkit-scrollbar-track {{
            background: #f1f1f1;
        }}
        
        ::-webkit-scrollbar-thumb {{
            background: var(--primary-color);
            border-radius: 4px;
        }}
        
        ::-webkit-scrollbar-thumb:hover {{
            background: #1d4ed8;
        }}
    </style>
</head>
<body>
    <div class="dashboard-container">
        <!-- Header -->
        <div class="dashboard-header">
            <h1 class="dashboard-title">{dashboard_title}</h1>
            <p class="dashboard-subtitle">
                <i class="fas fa-chart-line"></i> 
                Interactive Data Analysis & Visualization Dashboard
            </p>
            <div class="mt-3">
                <span class="badge bg-primary me-2">
                    <i class="fas fa-table"></i> {analysis['total_rows']:,} Rows
                </span>
                <span class="badge bg-secondary me-2">
                    <i class="fas fa-columns"></i> {analysis['total_columns']} Columns
                </span>
                <span class="badge bg-info">
                    <i class="fas fa-clock"></i> Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </span>
            </div>
        </div>
        
        <!-- Key Insights -->
        <div class="row mb-4">
            <div class="col-12">
                <h2 class="mb-4">
                    <i class="fas fa-lightbulb text-warning"></i> 
                    Key Insights
                </h2>
            </div>
        </div>
        
        <div class="stats-grid">
            {self._generate_insight_cards(insights)}
        </div>
        
        <!-- Column Analysis -->
        <div class="row mb-4">
            <div class="col-12">
                <h2 class="mb-4">
                    <i class="fas fa-columns text-primary"></i> 
                    Column Analysis
                </h2>
            </div>
        </div>
        
        <div class="row">
            {self._generate_column_analysis_cards(analysis)}
        </div>
        
        <!-- Visualizations -->
        <div class="row mb-4">
            <div class="col-12">
                <h2 class="mb-4">
                    <i class="fas fa-chart-pie text-success"></i> 
                    Data Visualizations
                </h2>
            </div>
        </div>
        
        {self._generate_chart_sections(analysis, chart_data)}
        
        <!-- Data Preview -->
        <div class="data-table-container">
            <h3 class="mb-4">
                <i class="fas fa-table text-info"></i> 
                Data Preview
            </h3>
            <div class="table-responsive">
                <table id="dataTable" class="table table-striped table-hover">
                    <thead class="table-primary">
                        <tr>
                            {self._generate_table_headers(analysis)}
                        </tr>
                    </thead>
                    <tbody>
                        <!-- Data will be loaded via JavaScript -->
                    </tbody>
                </table>
            </div>
        </div>
        
        <!-- Footer -->
        <div class="text-center mt-5 pt-4 border-top">
            <p class="text-muted">
                <i class="fas fa-robot"></i> 
                Dashboard generated by Puch AI CSV Dashboard Generator
                <br>
                <small>Powered by AI • Interactive Analytics • Beautiful Visualizations</small>
            </p>
        </div>
    </div>
    
    <!-- Bootstrap JS -->
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    
    <!-- DataTables JS -->
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <script src="https://cdn.datatables.net/1.13.6/js/dataTables.bootstrap5.min.js"></script>
    
    <script>
        // Chart data from Python
        const chartData = {json.dumps(chart_data)};
        const analysis = {json.dumps(analysis)};
        
        // Initialize charts when page loads
        document.addEventListener('DOMContentLoaded', function() {{
            initializeCharts();
            initializeDataTable();
        }});
        
        function initializeCharts() {{
            {self._generate_chart_javascript(analysis, chart_data)}
        }}
        
        function initializeDataTable() {{
            // Initialize DataTable with sample data
            $('#dataTable').DataTable({{
                "pageLength": 25,
                "order": [],
                "responsive": true,
                "language": {{
                    "search": "Filter data:",
                    "lengthMenu": "Show _MENU_ rows per page",
                    "info": "Showing _START_ to _END_ of _TOTAL_ entries",
                    "paginate": {{
                        "next": "Next →",
                        "previous": "← Previous"
                    }}
                }},
                "columnDefs": [
                    {{ "className": "text-center", "targets": "_all" }}
                ]
            }});
        }}
        
        // Utility functions
        function formatNumber(num) {{
            return new Intl.NumberFormat().format(num);
        }}
        
        function getRandomColor() {{
            const colors = [
                '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
            ];
            return colors[Math.floor(Math.random() * colors.length)];
        }}
        
        // Show loading state
        function showLoading(elementId) {{
            document.getElementById(elementId).innerHTML = '<div class="text-center p-4"><div class="loading"></div><p class="mt-2">Loading chart...</p></div>';
        }}
    </script>
</body>
</html>"""
    
    def _generate_insight_cards(self, insights: List[Dict]) -> str:
        """Generate HTML for insight cards."""
        cards_html = ""
        
        for insight in insights:
            color_class = f"text-{insight['color']}"
            icon = insight.get('icon', 'fas fa-info-circle')
            
            details_html = ""
            if 'details' in insight:
                details_html = '<ul class="list-unstyled mt-2 small">'
                for detail in insight['details']:
                    details_html += f'<li><i class="fas fa-chevron-right me-1"></i> {detail}</li>'
                details_html += '</ul>'
            
            cards_html += f"""
            <div class="insight-card">
                <div class="card-body text-center">
                    <div class="insight-icon {color_class}">
                        <i class="{icon}"></i>
                    </div>
                    <div class="insight-value {color_class}">{insight['value']}</div>
                    <div class="insight-title">{insight['title']}</div>
                    <div class="insight-message">{insight['message']}</div>
                    {details_html}
                </div>
            </div>
            """
        
        return cards_html
    
    def _generate_column_analysis_cards(self, analysis: Dict) -> str:
        """Generate HTML cards for column analysis."""
        cards_html = ""
        
        for column, col_analysis in analysis['column_analysis'].items():
            dtype = analysis['data_types'][column]
            missing_pct = analysis['missing_values'][column]['percentage']
            quality_score = col_analysis['data_quality_score']
            
            # Determine color based on data type
            type_colors = {
                'numeric': 'primary',
                'categorical': 'success', 
                'datetime': 'info',
                'text': 'secondary'
            }
            
            type_icons = {
                'numeric': 'fas fa-calculator',
                'categorical': 'fas fa-tags',
                'datetime': 'fas fa-calendar',
                'text': 'fas fa-font'
            }
            
            color = type_colors.get(dtype, 'secondary')
            icon = type_icons.get(dtype, 'fas fa-question-circle')
            
            # Quality badge
            quality_color = 'success' if quality_score >= 80 else 'warning' if quality_score >= 60 else 'danger'
            
            cards_html += f"""
            <div class="col-md-6 col-lg-4 mb-4">
                <div class="card h-100 insight-card">
                    <div class="card-body">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <h5 class="card-title text-{color}">
                                <i class="{icon} me-2"></i>
                                {column}
                            </h5>
                            <span class="badge bg-{quality_color}">{quality_score:.0f}%</span>
                        </div>
                        
                        <div class="mb-2">
                            <small class="text-muted">Type:</small>
                            <span class="badge bg-{color} ms-1">{dtype.title()}</span>
                        </div>
                        
                        <div class="mb-2">
                            <small class="text-muted">Unique Values:</small>
                            <strong class="ms-1">{col_analysis['unique_values']:,}</strong>
                        </div>
                        
                        <div class="mb-2">
                            <small class="text-muted">Missing:</small>
                            <strong class="ms-1">{missing_pct:.1f}%</strong>
                        </div>
                        
                        {self._generate_column_specific_info(column, dtype, analysis)}
                    </div>
                </div>
            </div>
            """
        
        return cards_html
    
    def _generate_column_specific_info(self, column: str, dtype: str, analysis: Dict) -> str:
        """Generate column-specific information based on data type."""
        if dtype == 'numeric' and column in analysis['statistics']:
            stats = analysis['statistics'][column]
            return f"""
            <div class="mt-3">
                <small class="text-muted">Statistics:</small>
                <div class="small">
                    <div>Mean: <strong>{stats['mean']:.2f}</strong></div>
                    <div>Range: <strong>{stats['min']:.2f} - {stats['max']:.2f}</strong></div>
                </div>
            </div>
            """
        elif dtype == 'categorical' and 'frequency_distribution' in analysis['column_analysis'][column]:
            freq = analysis['column_analysis'][column]['frequency_distribution']
            top_value = list(freq.keys())[0] if freq else "N/A"
            return f"""
            <div class="mt-3">
                <small class="text-muted">Most Frequent:</small>
                <div class="small">
                    <strong>{top_value}</strong>
                </div>
            </div>
            """
        return ""
    
    def _generate_chart_sections(self, analysis: Dict, chart_data: Dict) -> str:
        """Generate chart sections based on recommended charts."""
        sections_html = ""
        
        for i, recommendation in enumerate(analysis['recommended_charts'][:6]):  # Limit to 6 charts
            chart_id = f"chart_{i}"
            sections_html += f"""
            <div class="col-12 mb-4">
                <div class="chart-container">
                    <h4 class="chart-title">{recommendation['title']}</h4>
                    <p class="text-muted text-center mb-4">{recommendation['description']}</p>
                    <div class="position-relative" style="height: 400px;">
                        <canvas id="{chart_id}"></canvas>
                    </div>
                </div>
            </div>
            """
        
        return sections_html
    
    def _generate_table_headers(self, analysis: Dict) -> str:
        """Generate table headers."""
        headers = ""
        for column in analysis['columns']:
            headers += f'<th>{column}</th>'
        return headers
    
    def _generate_chart_javascript(self, analysis: Dict, chart_data: Dict) -> str:
        """Generate JavaScript code for initializing charts."""
        js_code = ""
        
        numeric_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'numeric']
        categorical_cols = [col for col, dtype in analysis['data_types'].items() if dtype == 'categorical']
        
        chart_count = 0
        
        # Generate charts based on recommendations
        for i, recommendation in enumerate(analysis['recommended_charts'][:6]):
            chart_id = f"chart_{i}"
            chart_type = recommendation['chart_type']
            
            if chart_type == 'bar' and categorical_cols and numeric_cols:
                cat_col = categorical_cols[0]
                if cat_col in chart_data:
                    js_code += f"""
                    new Chart(document.getElementById('{chart_id}'), {{
                        type: 'bar',
                        data: {{
                            labels: {json.dumps(chart_data[cat_col]['labels'])},
                            datasets: [{{
                                label: '{cat_col}',
                                data: {json.dumps(chart_data[cat_col]['values'])},
                                backgroundColor: 'rgba(37, 99, 235, 0.7)',
                                borderColor: 'rgba(37, 99, 235, 1)',
                                borderWidth: 2,
                                borderRadius: 8
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    display: false
                                }},
                                tooltip: {{
                                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                                    titleColor: '#fff',
                                    bodyColor: '#fff'
                                }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    grid: {{
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }}
                                }},
                                x: {{
                                    grid: {{
                                        display: false
                                    }}
                                }}
                            }}
                        }}
                    }});
                    """
            
            elif chart_type == 'line' and numeric_cols:
                num_col = numeric_cols[0]
                if num_col in chart_data:
                    labels = [f"Point {i+1}" for i in range(len(chart_data[num_col]))]
                    js_code += f"""
                    new Chart(document.getElementById('{chart_id}'), {{
                        type: 'line',
                        data: {{
                            labels: {json.dumps(labels)},
                            datasets: [{{
                                label: '{num_col}',
                                data: {json.dumps(chart_data[num_col])},
                                borderColor: 'rgba(37, 99, 235, 1)',
                                backgroundColor: 'rgba(37, 99, 235, 0.1)',
                                borderWidth: 3,
                                tension: 0.4,
                                fill: true
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    display: false
                                }}
                            }},
                            scales: {{
                                y: {{
                                    beginAtZero: true,
                                    grid: {{
                                        color: 'rgba(0, 0, 0, 0.05)'
                                    }}
                                }},
                                x: {{
                                    grid: {{
                                        display: false
                                    }}
                                }}
                            }}
                        }}
                    }});
                    """
            
            elif chart_type == 'pie' and categorical_cols:
                cat_col = categorical_cols[0]
                if cat_col in chart_data:
                    js_code += f"""
                    new Chart(document.getElementById('{chart_id}'), {{
                        type: 'pie',
                        data: {{
                            labels: {json.dumps(chart_data[cat_col]['labels'])},
                            datasets: [{{
                                data: {json.dumps(chart_data[cat_col]['values'])},
                                backgroundColor: [
                                    '#FF6384', '#36A2EB', '#FFCE56', '#4BC0C0', 
                                    '#9966FF', '#FF9F40', '#FF6384', '#C9CBCF'
                                ],
                                borderWidth: 2,
                                borderColor: '#fff'
                            }}]
                        }},
                        options: {{
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {{
                                legend: {{
                                    position: 'bottom',
                                    labels: {{
                                        padding: 20,
                                        usePointStyle: true
                                    }}
                                }}
                            }}
                        }}
                    }});
                    """
        
        return js_code


# Helper functions for data processing
def detect_data_type(series):
    """Detect the most appropriate data type for a pandas Series."""
    if pd.api.types.is_numeric_dtype(series):
        return 'numeric'
    elif pd.api.types.is_datetime64_any_dtype(series):
        return 'datetime'
    elif series.nunique() / len(series) < 0.5:
        return 'categorical'
    else:
        return 'text'


def calculate_correlation_matrix(df, numeric_columns):
    """Calculate correlation matrix for numeric columns."""
    if len(numeric_columns) < 2:
        return None
    
    numeric_df = df[numeric_columns].select_dtypes(include=[np.number])
    return numeric_df.corr().to_dict()


def detect_outliers(series):
    """Detect outliers using IQR method."""
    if not pd.api.types.is_numeric_dtype(series):
        return []
    
    Q1 = series.quantile(0.25)
    Q3 = series.quantile(0.75)
    IQR = Q3 - Q1
    
    lower_bound = Q1 - 1.5 * IQR
    upper_bound = Q3 + 1.5 * IQR
    
    outliers = series[(series < lower_bound) | (series > upper_bound)]
    return outliers.tolist()
