# File: main.py
# Corrected for Netlify Deployment

import pandas as pd
import re
from urllib.parse import urlparse
from flask import Flask, render_template, request, send_file
import io # Used for creating the file in memory

# BINGO: This is the fix.
# By removing the template_folder and static_folder arguments,
# Flask will correctly look for them in the root directory.
app = Flask(__name__)


# --- Helper Functions (No changes needed, your logic is good) ---

def get_urls_from_excel(file_storage):
    """Reads an uploaded file and extracts all URLs from its cells."""
    urls = set()
    url_regex = re.compile(r'https?:\/\/[^\s/$.?#].[^\s]*', re.IGNORECASE)
    
    try:
        xls = pd.ExcelFile(file_storage)
        for sheet_name in xls.sheet_names:
            df = pd.read_excel(xls, sheet_name=sheet_name, header=None)
            for col in df.columns:
                for item in df[col]:
                    if isinstance(item, str):
                        found_urls = url_regex.findall(item)
                        for url in found_urls:
                            urls.add(url.strip())
    except Exception as e:
        print(f"Error reading Excel file: {e}")
        pass
        
    return list(urls)

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
            return hostname
        
        slds = {'co', 'com', 'org', 'net', 'gov', 'edu', 'ac'}
        
        if len(parts) > 2 and parts[-2] in slds:
            return ".".join(parts[-3:])
        else:
            return ".".join(parts[-2:])
    except Exception:
        return None

# --- Flask Routes (No changes needed, your logic is good) ---

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        existing_file = request.files.get('existing_file')
        prospect_file = request.files.get('prospect_file')

        if not existing_file or not prospect_file:
            return "Both files are required.", 400

        existing_urls = get_urls_from_excel(existing_file)
        existing_domains = {get_root_domain(url) for url in existing_urls if get_root_domain(url)}

        prospect_urls = get_urls_from_excel(prospect_file)

        unique_prospects = []
        duplicate_prospects = []
        
        for url in prospect_urls:
            domain = get_root_domain(url)
            if domain:
                if domain in existing_domains:
                    duplicate_prospects.append({'Prospect URL': url, 'Matches Existing Domain': domain})
                else:
                    unique_prospects.append({'URL': url})

        output = io.BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            pd.DataFrame(unique_prospects).to_excel(writer, sheet_name='Unique Prospects', index=False)
            pd.DataFrame(duplicate_prospects).to_excel(writer, sheet_name='Duplicate Prospects', index=False)
        
        output.seek(0)

        return send_file(
            output,
            as_attachment=True,
            download_name='Unique_Prospects_Report.xlsx',
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

    return render_template('index.html')

# --- Run the App ---
if __name__ == '__main__':
    app.run(debug=True)
