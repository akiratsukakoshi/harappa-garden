import gspread
import os
import sys
import pandas as pd
from datetime import datetime
from google.oauth2.service_account import Credentials
from modules.utils import setup_logger

logger = setup_logger("SheetSyncer")

# Scopes required
SCOPES = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive'
]

SHEET_URL = "https://docs.google.com/spreadsheets/d/1y1zfz8bh4mtACC28SNdoH6lp45s_JHI_1MOVVXr0zKc/edit"

class SheetSyncer:
    def __init__(self, key_path="credentials.json"):
        if not os.path.exists(key_path):
            raise FileNotFoundError(f"Credentials file not found at: {key_path}")
        
        creds = Credentials.from_service_account_file(key_path, scopes=SCOPES)
        self.client = gspread.authorize(creds)
        
        try:
            self.spreadsheet = self.client.open_by_url(SHEET_URL)
            logger.info(f"Connected to Spreadsheet: {self.spreadsheet.title}")
        except Exception as e:
            logger.error(f"Failed to open spreadsheet: {e}")
            raise e

    def get_worksheet(self, name):
        try:
            return self.spreadsheet.worksheet(name)
        except gspread.WorksheetNotFound:
            logger.error(f"Worksheet '{name}' not found.")
            return None

    def update_actuals(self, sheet_name, data_map, date_row_index=1, item_col_index=1):
        """
        Smart update that searches for intersection of Date (column) and Item (row).
        
        data_map: dict
          {
             "2024-01": { "売上高": 10000, "営業利益": 5000 },
             "2024-02": { ... }
          }
        
        date_row_index: 1-based index of the row containing dates (e.g., Apr, May...)
        item_col_index: 1-based index of the column containing items (e.g., Sales, Profit...)
        """
        ws = self.get_worksheet(sheet_name)
        if not ws:
            return

        # 1. Fetch Header Row and Key Column to map positions
        # Note: Getting all values is faster than cell-by-cell
        all_values = ws.get_all_values()
        
        if len(all_values) < date_row_index:
            logger.error("Sheet is too empty.")
            return

        # Map Dates to Column Indices (0-based in list, +1 for gspread)
        # Assuming dates might be strings "2024-04" or "4月".
        # Implementation depends heavily on Sheet format.
        # For now, we fetch the header row
        header_row_values = all_values[date_row_index - 1] 
        
        # Map Items to Row Indices
        item_row_map = {}
        for r_idx, row_val in enumerate(all_values):
            # item_col_index - 1 because list is 0-indexed
            if len(row_val) >= item_col_index:
                item_name = row_val[item_col_index - 1].strip()
                if item_name:
                    item_row_map[item_name] = r_idx + 1 # 1-based
        
        # Map Dates
        date_col_map = {}
        for c_idx, val in enumerate(header_row_values):
            clean_val = val.strip()
            # Try to normalize date if possible, or expect exact match
            if clean_val:
                date_col_map[clean_val] = c_idx + 1 # 1-based

        updates = []
        
        for date_key, items_dict in data_map.items():
            # Check matches for Date
            # Try exact match first
            col_idx = date_col_map.get(date_key)
            
            # TODO: Add fuzzy date matching if needed (e.g. 2024-04 vs 4月)
            
            if not col_idx:
                logger.warning(f"Date column '{date_key}' not found in sheet '{sheet_name}'. Skipping.")
                continue

            for item_name, value in items_dict.items():
                row_idx = item_row_map.get(item_name)
                if row_idx:
                    # Prepare update
                    # gspread update_cells is efficient, or batch_update
                    # For now just collect cells
                    updates.append({
                        'range': gspread.utils.rowcol_to_a1(row_idx, col_idx),
                        'values': [[value]]
                    })
                else:
                    logger.debug(f"Item row '{item_name}' not found in sheet '{sheet_name}'.")

        if updates:
            logger.info(f"Updating {len(updates)} cells in '{sheet_name}'...")
            ws.batch_update(updates)
            logger.info("Update complete.")
        else:
            logger.info("No updates prepared.")

    def create_worksheet(self, title, rows, cols=20):
        try:
            ws = self.get_worksheet(title)
            if ws:
                logger.info(f"Worksheet '{title}' already exists. Resizing to {cols} cols...")
                # Resize if needed (naive resize)
                ws.resize(rows=ws.row_count, cols=max(ws.col_count, cols))
                return ws
            
            logger.info(f"Creating worksheet '{title}'...")
            ws = self.spreadsheet.add_worksheet(title, rows=len(rows)+10, cols=cols)
            ws.update('A1', rows)
            return ws
        except Exception as e:
            logger.error(f"Failed to create worksheet '{title}': {e}")
            raise e

    def sync_row_headers(self, sheet_name, row_headers, start_row=2, col_index=1):
        """
        Overwrite the row headers (e.g. Column A) with the provided list.
        """
        ws = self.get_worksheet(sheet_name)
        if not ws:
            return
            
        # Prepare content: vertical list
        cell_values = [[h] for h in row_headers]
        
        # Range: A2:A(N)
        end_row = start_row + len(row_headers) - 1
        range_str = gspread.utils.rowcol_to_a1(start_row, col_index) + ":" + gspread.utils.rowcol_to_a1(end_row, col_index)
        
        logger.info(f"Syncing {len(row_headers)} row headers to '{sheet_name}'...")
        ws.update(range_str, cell_values)

    def update_data_block(self, sheet_name, data_matrix, start_row=2, start_col=2):
        """
        Update a block of data positionally.
        data_matrix: List of Lists [[val, val], [val, val]]
        """
        ws = self.get_worksheet(sheet_name)
        if not ws or not data_matrix:
            return
            
        rows = len(data_matrix)
        cols = len(data_matrix[0])
        
        # Calculate Range: B2:M(N)
        # start_col=2 (B)
        start_a1 = gspread.utils.rowcol_to_a1(start_row, start_col)
        end_a1 = gspread.utils.rowcol_to_a1(start_row + rows - 1, start_col + cols - 1)
        range_str = f"{start_a1}:{end_a1}"
        
        logger.info(f"Updating data block {rows}x{cols} in '{sheet_name}' at {range_str}...")
        ws.update(range_str, data_matrix)

