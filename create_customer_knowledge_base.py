import pandas as pd

def create_customer_knowledge_base():
    # Define Customers data
    customers_data = {
        'CustomerID': [1, 2, 3],
        'Name': ['Alice Smith', 'Bob Johnson', 'Charlie Lee'],
        'Email': ['alice@example.com', 'bob@example.com', 'charlie@example.com'],
        'Phone': ['123-456-7890', '234-567-8901', '345-678-9012'],
        'Address': ['123 Maple St', '456 Oak St', '789 Pine St']
    }
    customers_df = pd.DataFrame(customers_data)

    # Define Orders data
    orders_data = {
        'OrderID': [101, 102, 103],
        'CustomerID': [1, 2, 3],  # Foreign key to Customers
        'OrderDate': ['2024-01-15', '2024-02-20', '2024-03-05'],
        'Amount': [250.00, 450.00, 125.00]
    }
    orders_df = pd.DataFrame(orders_data)

    # Create a Pandas Excel writer using XlsxWriter as the engine
    with pd.ExcelWriter('data/customer_knowledge_base.xlsx', engine='xlsxwriter') as writer:
        # Write each dataframe to a different worksheet
        customers_df.to_excel(writer, sheet_name='Customers', index=False)
        orders_df.to_excel(writer, sheet_name='Orders', index=False)

        # Get the xlsxwriter workbook and worksheets objects
        workbook  = writer.book
        customers_sheet = writer.sheets['Customers']
        orders_sheet = writer.sheets['Orders']

        # Add a format for the primary key columns (bold)
        pk_format = workbook.add_format({'bold': True, 'bg_color': '#D7E4BC'})

        # Format primary key columns in Customers sheet (CustomerID)
        customers_sheet.set_column('A:A', 12, pk_format)

        # Format primary key and foreign key columns in Orders sheet (OrderID and CustomerID)
        orders_sheet.set_column('A:A', 10, pk_format)
        orders_sheet.set_column('B:B', 12, pk_format)

if __name__ == '__main__':
    create_customer_knowledge_base()
    print("Excel knowledge base created at 'data/customer_knowledge_base.xlsx'")
