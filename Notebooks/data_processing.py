import pandas as pd

class DataProcessing:
    """
     This class will have data cleaning and processing methods
    """
    def __init__(self, dataframe):
        self.dataframe = dataframe

    def check_data(self):
        """
        Check for null, duplicared and null values
        Parameters:
            - dataframe: pandas DataFrame  
        """
        columns_to_exclude = [col for col, dtype in self.dataframe.dtypes.items() 
                              if dtype == 'object' and isinstance(self.dataframe[col][0], list)]

        missing_values = self.dataframe.isnull().sum()
        unique_values = self.dataframe.drop(columns=columns_to_exclude).nunique()

        #Drop list before checking duplicate values
        without_list_columns = self.dataframe.drop(columns=columns_to_exclude)
        duplicated_rows = without_list_columns.duplicated().sum()
        
        result = pd.DataFrame({
            "Missing values": missing_values,
            "Duplicated values": duplicated_rows,
            "Unique values": unique_values
        })

        return result

    def drop_columns_if_exist(self, dataframe, columns_to_drop):
        """
        Drop specified columns from a DataFrame if they exist.
        Parameters:
            - dataframe: pandas DataFrame
            - columns_to_drop: list of column names to be dropped
    
        """
        existing_columns = set(dataframe.columns)
        columns_to_drop_existing = [col for col in columns_to_drop if col in existing_columns]
    
        if columns_to_drop_existing:
            dataframe.drop(columns=columns_to_drop_existing, inplace=True)
            print(f"Dropped columns: {columns_to_drop_existing}")
        else:
            print("Columns not found. No columns dropped.")


