import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import requests
import chardet
import numpy as np
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error
from sklearn.model_selection import train_test_split

# API Setup
AIPROXY_TOKEN = os.environ["AIPROXY_TOKEN"]

if not AIPROXY_TOKEN:
    raise ValueError("AIPROXY_TOKEN environment variable is not set.")

HEADERS = {
    "Content-Type": "application/json",
    "Authorization": f"Bearer {AIPROXY_TOKEN}"
}


def read_csv_with_fallback(csv_path):
    """Reads a CSV file with automatic encoding detection and fallback options."""
    try:
        with open(csv_path, 'rb') as f:
            encoding = chardet.detect(f.read())['encoding']
            return pd.read_csv(csv_path, encoding=encoding)
    except Exception:
        return pd.read_csv(csv_path, encoding='utf-8', errors='ignore')


def summarize_numerical_data(df):
    """Summarizes numerical data (excluding 'id' and 'isbn')."""
    numerical_cols = [col for col in df.select_dtypes(include=['number']).columns if 'id' not in col.lower() and 'isbn' not in col.lower()]
    return df[numerical_cols].describe().round(2) if numerical_cols else pd.DataFrame()


def calculate_correlation(df):
    """Calculates the correlation matrix for numerical columns."""
    exclude_keywords = ['title', 'image', 'url', 'path', 'description']
    numerical_cols = [col for col in df.select_dtypes(include=['number']).columns if not any(keyword in col.lower() for keyword in exclude_keywords)]
    return df[numerical_cols].corr().round(2) if numerical_cols else pd.DataFrame()


def generate_insights(csvfile,cols,summary_stats, correlation_matrix, mse):
    """Generates insights from the summary statistics and correlation matrix using GPT API."""
    prompt = f"""
    This is a csvfile datset named {csvfile}, and has columns list namely {cols},
    Summary Statistics of dataset:
    {summary_stats}

    Correlation Matrix of numerical cols:
    {correlation_matrix}

    Regression Analysis Mean Squared Errors: {mse}

    Write a detailed data report like story about your analysis, including data insights and implications.
    """
    url = "http://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
    data = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": prompt}]}
    response = requests.post(url, json=data, headers=HEADERS)
    if response.status_code == 200:
        return response.json()['choices'][0]['message']['content']
    return ""


def generate_graphs(df, output_dir):
    """Generates graphs based on dataset and user-specified suggestions."""
    numerical_cols = [col for col in df.select_dtypes(include=['number']).columns if 'id' not in col.lower() and 'isbn' not in col.lower()]
    if not numerical_cols:
        return []

    graph_evaluations = []
    graph_evaluations.extend(generate_histograms(df, numerical_cols, output_dir))
    graph_evaluations.extend(generate_scatter_plots(df, numerical_cols, output_dir))
    graph_evaluations.append(generate_correlation_heatmap(df, numerical_cols, output_dir))

    return graph_evaluations


def generate_histograms(df, numerical_cols, output_dir):
    """Generates histograms for numerical columns."""
    histograms = []
    for col in numerical_cols:
        plt.figure(figsize=(10, 6))
        sns.histplot(df[col], kde=True, color="skyblue", bins=20, edgecolor="black")
        plt.title(f"Distribution of {col}", fontsize=16)
        plt.xlabel(col, fontsize=14)
        plt.ylabel("Frequency", fontsize=14)
        plt.tight_layout()
        file_path = os.path.join(output_dir, f"{col}_histogram.png")
        plt.savefig(file_path, dpi=300)
        plt.close()
        histograms.append(file_path)
    return histograms


def generate_scatter_plots(df, numerical_cols, output_dir):
    """Generates scatter plots for highly correlated pairs."""
    corr_matrix = df[numerical_cols].corr().abs()
    upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    high_corr_pairs = [(col1, col2) for col1 in upper_tri.columns for col2 in upper_tri.index if upper_tri.loc[col2, col1] >= 0.5]

    scatter_plots = []
    for col_x, col_y in high_corr_pairs[:5]:
        plt.figure(figsize=(10, 6))
        sns.scatterplot(x=df[col_x], y=df[col_y], color="orange", s=100, edgecolor="black")
        plt.title(f"Scatter plot: {col_x} vs {col_y}", fontsize=16)
        plt.xlabel(col_x, fontsize=14)
        plt.ylabel(col_y, fontsize=14)
        plt.tight_layout()
        file_path = os.path.join(output_dir, f"{col_x}_vs_{col_y}_scatter.png")
        plt.savefig(file_path, dpi=300)
        plt.close()
        scatter_plots.append(file_path)
    return scatter_plots


def generate_correlation_heatmap(df, numerical_cols, output_dir):
    """Generates a correlation heatmap for the numerical columns."""
    correlation_matrix = df[numerical_cols].corr()
    plt.figure(figsize=(12, 10))
    sns.heatmap(correlation_matrix, annot=True, cmap='coolwarm', fmt='.2f', linewidths=0.5, cbar_kws={'shrink': 0.8}, annot_kws={'size': 12})
    plt.title("Correlation Heatmap", fontsize=18)
    plt.tight_layout()
    file_path = os.path.join(output_dir, "correlation_heatmap.png")
    plt.savefig(file_path, dpi=300)
    plt.close()
    return file_path


def perform_regression_analysis(df, numerical_cols, output_dir):
    """Performs regression analysis on highly correlated numerical columns."""
    corr_matrix = df[numerical_cols].corr().abs()
    upper_tri = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    high_corr_pairs = [(col1, col2) for col1 in upper_tri.columns for col2 in upper_tri.index if upper_tri.loc[col2, col1] >= 0.7]

    mse_list = []
    regression_files = []
    for col_x, col_y in high_corr_pairs[:5]:
        data = df[[col_x, col_y]].dropna()
        X = data[[col_x]]
        y = data[col_y]

        if len(X) < 2 or len(y) < 2:
            continue

        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        regressor = LinearRegression()
        regressor.fit(X_train, y_train)
        y_pred = regressor.predict(X_test)
        
        mse = mean_squared_error(y_test, y_pred)
        equation_text = f"y = {regressor.coef_[0]:.2f}x + {regressor.intercept_:.2f} \nMSE: {mse:.2f}"
        
        plt.figure(figsize=(10, 6))
        sns.scatterplot(x=X_test[col_x], y=y_test, color="blue", label="Actual")
        sns.lineplot(x=X_test[col_x], y=y_pred, color="red", label="Regression Line")
        plt.text(0.05, 0.9, equation_text, fontsize=12, transform=plt.gca().transAxes,
                 bbox=dict(facecolor='white', alpha=0.5))
        plt.title(f"Regression Line: {col_x} vs {col_y} (MSE: {mse:.2f})", fontsize=16)
        plt.tight_layout()

        file_path = os.path.join(output_dir, f"{col_x}_vs_{col_y}_regression.png")
        plt.savefig(file_path, dpi=300)
        plt.close()
        regression_files.append(file_path)
        
        mse_list.append(f"{col_x} vs {col_y}: y = {regressor.coef_[0]:.2f}x + {regressor.intercept_:.2f}, MSE: {mse:.2f}")

    return mse_list, regression_files


def save_to_markdown(content, filename="README.md", directory="."):
    """Saves the provided content to a Markdown (.md) file."""
    try:
        if not os.path.exists(directory):
            os.makedirs(directory)

        file_path = os.path.join(directory, filename)
        with open(file_path, "w", encoding="utf-8") as file:
            file.write(content)

        return file_path
    except Exception as e:
        print(f"Error saving file: {e}")
        return None


def main():
    import sys
    if len(sys.argv) < 2:
        print("Please provide a CSV file as an argument.")
        return

    csv_path = sys.argv[1]

    if not os.path.isfile(csv_path):
        print("File does not exist.")
        return


    folder_name = os.path.splitext(os.path.basename(csv_path))[0]
    output_dir = os.path.join(os.path.dirname(csv_path), folder_name)

    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Data reading and analysis
    df = read_csv_with_fallback(csv_path)
    if df is None:
        print("Failed to read CSV.")
        return

    numerical_summary = summarize_numerical_data(df)
    correlation_matrix = calculate_correlation(df)
    mse_list = perform_regression_analysis(df, df.select_dtypes(include=['number']).columns, output_dir)
    insights = generate_insights(csv_path,df.columns.tolist(),numerical_summary, correlation_matrix, mse_list)

    # Generate and save outputs
    save_to_markdown(insights, directory=output_dir)
    
    # Generate graphs
    generate_graphs(df, output_dir)

    print("Analysis complete, graphs and reports generated.")

if __name__ == "__main__":
    main()
