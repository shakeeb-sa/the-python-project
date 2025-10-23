# File: main.py
import pandas as pd
import re
from urllib.parse import urlparse
from flask import Flask, render_template, request, send_file
import io # Used for creating the file in memory

# --- Configuration ---
# Use the same Flask app setup from your working project.
# This points Flask to the correct template and static folders.
app = Flask(__name__, template_folder='python_web_tool/templates', static_folder='python_web_tool/static')

# --- Helper Functions (Python version of your JS functions) ---

def get_urls_from_excel(file_storage):
    """Reads an uploaded file and extracts all URLs from its cells."""
    urls = set()  # Use a set to store unique URLs automatically
    url_regex = re.compile(r'https?:\/\/[^\s/$.?#].[^\s]*', re.IGNORECASE)
    
    try:
        # Read all sheets from the Excel file
        xls = pd.ExcelFile(file_storage)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            # Iterate over every cell in the DataFrame
            for col in df.columns:
                for item in df[col]:
                    if isinstance(item, str):
                        found_urls = url_regex.findall(item)
                        for url in found_urls:
                            urls.add(url.strip())
    except Exception as e:
        # Handle cases where the file might be corrupted or not a valid Excel file
        print(f"Error reading Excel file: {e}")
        # Depending on requirements, you could raise this error
        # or return an empty set. For robustness, we return what we have.
        pass
        
    return list(urls) # Return as a list

def get_root_domain(url):
    """Extracts the root domain (e.g., 'example.co.uk' or 'google.com') from a URL."""
    if not url:
        return None
    try:
        hostname = urlparse(url).hostname
        if not hostname:
            return None
        
        parts = hostname.lower().split('.')
        if len(parts) < 2:
            return hostname  # Handle cases like 'localhost'
        
        # Common second-level domains
        slds = {'co', 'com', 'org', 'net', 'gov', 'edu', 'ac'}
        
        if len(parts) > 2 and parts[-2] in slds:
            return ".".join(parts[-3:])
        else:
            return ".".join(parts[-2:])
    except Exception:
        return None # Invalid URL format

# --- Flask Routes ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 1. Get uploaded files from the form
        existing_file = request.files.get('existing_file')
        prospect_file = request.files.get('prospect_file')

        if not existing_file or not prospect_file:
            # This is a server-side validation check
            return "Both files are required.", 400

        # 2. Extract URLs and get root domains (same logic as JS)
        existing_urls = get_urls_from_excel(existing_file)
        existing_domains = {get_root_domain(url) for url in existing_urls if get_root_domain(url)}

        prospect_urls = get_urls_from_excel(prospect_file)

        # 3. Compare domains and find unique prospects
        unique_prospects = []
        duplicate_prospects = []
        
        for url in prospect_urls:
            domain = get_root_domain(url)
            if domain:
                if domain in existing_domains:
                    duplicate_prospects.append({'Prospect URL': url, 'Matches Existing Domain': domain})
                else:
                    unique_prospects.append({'URL': url})

        # 4. Generate the output Excel file in memory
        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame(unique_prospects).to_excel(writer, sheet_name='Unique Prospects', index=False)
            pd.DataFrame(duplicate_prospects).to_excel(writer, sheet_name='Duplicate Prospects', index=False)
        
        output.seek(0) # Move the cursor to the beginning of the file-like object

        # 5. Send the file to the user for download
        return send_file(
            output,
            as_attachment=True,
            download_name='Unique_Prospects_Report.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    # For a GET request, just show the page
    return render_template('index.html')

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)