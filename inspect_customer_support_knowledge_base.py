import pandas as pd

def inspect_excel_file(file_path):
    # Load the Excel file
    xls = pd.ExcelFile(file_path)
    print(f"Sheet names: {xls.sheet_names}")

    # Read first 5 rows of each sheet
    for sheet in xls.sheet_names:
        df = pd.read_excel(xls, sheet_name=sheet)
        print(f"Sheet: {sheet}")
        print(df.head())
        print("-" * 40)

if __name__ == "__main__":
    inspect_excel_file("data/customer_support_knowledge_base.xlsx")
