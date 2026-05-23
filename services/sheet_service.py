import pandas as pd
import os

class SheetService:
    def __init__(self, data_dir="data"):
        self.data_dir = data_dir
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)

    def parse_sheet(self, file_path_or_url):
        """
        Parses an Excel file OR Google Sheet URL.
        """
        try:
            if file_path_or_url.startswith("http"):
                return self._parse_google_sheet(file_path_or_url)
            else:
                return self._parse_local_excel(file_path_or_url)
        except Exception as e:
            return f"Error parsing sheet: {e}"

    def _parse_local_excel(self, file_path):
        # Read the excel file
        # We treat the first sheet as the character sheet
        df = pd.read_excel(file_path, sheet_name=0)
        return self._dataframe_to_markdown(df, source_name=os.path.basename(file_path))

    def _parse_google_sheet(self, url):
        # Extract ID and GID
        import re
        import requests
        import io
        
        # Regex to find /d/ID/ and gid=GID
        id_match = re.search(r'/d/([a-zA-Z0-9-_]+)', url)
        if not id_match:
            return "Invalid Google Sheet URL. Could not find Sheet ID."
        
        sheet_id = id_match.group(1)
        
        gid_match = re.search(r'[#&?]gid=(\d+)', url)
        gid = gid_match.group(1) if gid_match else "0"
        
        export_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=csv&gid={gid}"
        
        # Fetch
        response = requests.get(export_url)
        if response.status_code != 200:
            return f"Could not download sheet. Ensure 'Anyone with the link' is set to 'Viewer'. (Status: {response.status_code})"
        
        df = pd.read_csv(io.StringIO(response.text))
        return self._dataframe_to_markdown(df, source_name="Google Sheet")

    def _dataframe_to_markdown(self, df, source_name):
        # Cleaning: Drop completely empty rows/cols
        df.dropna(how='all', inplace=True)
        df.dropna(axis=1, how='all', inplace=True)
        
        # Convert to a string representation (Markdown Table style)
        markdown_table = df.to_markdown(index=False)
        
        summary = f"Character Sheet ({source_name}):\n{markdown_table}"
        return summary
