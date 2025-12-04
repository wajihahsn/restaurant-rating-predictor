from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS
import os
import csv

# Try to import pandas but allow fallback
try:
    import pandas as pd
    print("[OK] Pandas imported successfully")
except Exception as e:
    print(f"[ERROR] Failed to import pandas: {e}")
    pd = None

app = Flask(__name__)
CORS(app)

# Loading the trained model (use absolute path so it works when started from other CWDs)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CSV_PATH = os.path.join(BASE_DIR, 'zomato_cleaned.csv')

# Load cleaned dataset for dropdowns if pandas is available
print(f"Attempting to load CSV from: {CSV_PATH}")
print(f"File exists: {os.path.exists(CSV_PATH)}")
try:
    if pd is not None:
        print("Loading CSV file... (this may take 30-60 seconds for large files)")
        df = pd.read_csv(CSV_PATH)
        print(f"[OK] CSV loaded successfully! {len(df)} rows, {len(df.columns)} columns")
    else:
        print("[ERROR] Pandas not available, cannot load CSV")
        df = None
except Exception as e:
    print(f'[ERROR] Could not read CSV: {e}')
    import traceback
    traceback.print_exc()
    df = None

# Function to read CSV as list of dicts (fallback for when pandas unavailable)
def read_csv_simple(filepath, num_rows=50):
    """Read CSV file using pure Python (no pandas required)"""
    try:
        rows = []
        csv.field_size_limit(10**7)  # Increase field size limit to 10MB
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            reader = csv.DictReader(f)
            for i, row in enumerate(reader):
                if i >= num_rows:
                    break
                rows.append(row)
        return rows
    except Exception as e:
        print(f"Error reading CSV: {e}")
        import traceback
        traceback.print_exc()
        return None

# Rule-based prediction (fallback / workaround for sklearn import issues)
def predict_rating(online_order, book_table, votes, approx_cost, location):
    """
    Simple linear prediction model based on feature weights.
    This replaces the pickled sklearn model to avoid dependency issues.
    """
    base = 3.5
    
    # Feature weights (tuned heuristically)
    online_order_weight = 0.2
    book_table_weight = 0.15
    votes_weight = (votes / 10000.0) * 1.2
    cost_weight = (approx_cost / 5000.0) * 0.8
    location_weight = (location / 94.0) * 0.3  # 94 locations max
    
    pred = (base + 
            online_order * online_order_weight +
            book_table * book_table_weight +
            votes_weight +
            cost_weight +
            location_weight)
    
    # Clip to valid range
    pred = max(1.0, min(5.0, pred))
    return round(pred, 1)

# Routes for HTML pages
@app.route('/')
def home():
    return render_template('home.html')

@app.route('/predictor')
def predictor():
    return render_template('predictor.html')

@app.route('/dashboard')
def dashboard():
    return render_template('dashboard.html')

@app.route('/dashboard-simple')
def dashboard_simple():
    return render_template('dashboard_simple.html')

@app.route('/data/zomato_cleaned.csv')
def download_data():
    return send_from_directory(BASE_DIR, 'zomato_cleaned.csv', as_attachment=True)

@app.route('/view-data')
def view_data():
    try:
        # Get file size
        file_size_mb = os.path.getsize(CSV_PATH) / (1024 * 1024)
        
        # Try pandas first, then fallback to CSV reader
        if df is not None:
            # Limit to first 50 rows for performance
            df_display = df.head(50)
            html_table = df_display.to_html(classes='data-table', border=0)
            total_records = len(df)
        else:
            rows = read_csv_simple(CSV_PATH, num_rows=50)
            if rows:
                total_records = "Unknown (>50)"
                headers = list(rows[0].keys()) if rows else []
                html_table = '<table class="data-table" border="0">\n<thead><tr>'
                for header in headers:
                    html_table += f'<th>{header}</th>'
                html_table += '</tr></thead>\n<tbody>'
                for row in rows:
                    html_table += '<tr>'
                    for header in headers:
                        val = str(row.get(header, ""))[:100]  # Truncate long values
                        html_table += f'<td>{val}</td>'
                    html_table += '</tr>'
                html_table += '</tbody>\n</table>'
            else:
                return "Could not read CSV file", 500
        
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Zomato Data</title>
            <style>
                body {{ font-family: Arial, sans-serif; padding: 20px; background: #f5f5f5; }}
                .info {{ background: white; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
                .data-table {{ border-collapse: collapse; background: white; width: 100%; }}
                .data-table th, .data-table td {{ padding: 8px; border: 1px solid #ddd; text-align: left; font-size: 11px; }}
                .data-table th {{ background: #003d3c; color: white; font-weight: bold; }}
                .data-table tr:hover {{ background: #f0f0f0; }}
            </style>
        </head>
        <body>
            <h1>Zomato Cleaned Data</h1>
            <div class="info">
                <p><strong>Total Records:</strong> {total_records}</p>
                <p><strong>File Size:</strong> {file_size_mb:.1f} MB</p>
                <p><em>Displaying first 50 records</em></p>
            </div>
            {html_table}
        </body>
        </html>
        """
    except Exception as e:
        print(f"Error in view_data: {str(e)}")
        import traceback
        traceback.print_exc()
        return f"Error loading data: {str(e)}", 500

# Prediction endpoint
@app.route('/predict', methods=['POST'])
def predict():
    try:
        # JSON data from frontend
        data = request.get_json()
        
        online_order = int(data['online_order'])  # 0 or 1
        book_table = int(data['book_table'])      # 0 or 1
        votes = int(data['votes'])
        approx_cost = float(data['approx_cost'])
        location = int(data['location'])
        
        # Use the rule-based predictor instead of sklearn model
        rating = predict_rating(online_order, book_table, votes, approx_cost, location)
        
        if rating >= 4.5:
            remark = "Excellent! ⭐⭐⭐⭐⭐"
        elif rating >= 4.0:
            remark = "Very Good! ⭐⭐⭐⭐"
        elif rating >= 3.5:
            remark = "Good ⭐⭐⭐"
        elif rating >= 3.0:
            remark = "Average ⭐⭐"
        else:
            remark = "Below Average ⭐"
        
        return jsonify({
            'rating': f"{rating}/5",
            'remark': remark
        })
    
    except Exception as e:
        print(f"Error in prediction: {str(e)}")  # For debugging
        return jsonify({'error': str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True, port=5000)