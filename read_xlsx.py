import pandas as pd
df = pd.read_excel('Schedule_Report_Improved_08-03-2026-15-02-40.xlsx')
print(df.head())
print("Columns:", df.columns.tolist())
