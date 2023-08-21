import pandas as pd
import matplotlib.pyplot as plt


class PandasUtility:
    def __init__(self):
        pass

    @staticmethod
    def print_dataframe(dataframe, num_rows=10):
        """
        Print the first few rows of a DataFrame.

        Args:
            dataframe (pandas.DataFrame): The DataFrame to be printed.
            num_rows (int, optional): Number of rows to display. Defaults to 10.
        """
        print(dataframe.head(num_rows))

    @staticmethod
    def visualize_dataframe(dataframe, x_column, y_column, plot_type='line'):
        """
        Visualize data in a DataFrame using matplotlib.

        Args:
            dataframe (pandas.DataFrame): The DataFrame containing the data.
            x_column (str): Name of the column to be used as the x-axis.
            y_column (str): Name of the column to be used as the y-axis.
            plot_type (str, optional): Type of plot ('line', 'scatter', etc.). Defaults to 'line'.
        """
        if plot_type == 'line':
            dataframe.plot(x=x_column, y=y_column, kind='line')
        elif plot_type == 'scatter':
            dataframe.plot(x=x_column, y=y_column, kind='scatter')
        else:
            raise ValueError("Unsupported plot type.")

        plt.xlabel(x_column)
        plt.ylabel(y_column)
        plt.title(f"{plot_type.capitalize()} Plot")
        plt.show()

    @staticmethod
    def organize_dataframe(dataframe, groupby_column, aggregation_functions):
        """
        Organize and aggregate data in a DataFrame.

        Args:
            dataframe (pandas.DataFrame): The DataFrame containing the data.
            groupby_column (str): Name of the column to group by.
            aggregation_functions (dict): Dictionary of column names and corresponding aggregation functions.

        Returns:
            pandas.DataFrame: The organized and aggregated DataFrame.
        """
        grouped_data = dataframe.groupby(
            groupby_column).agg(aggregation_functions)
        return grouped_data
