"""
Module for Data Fetching, Model Management, and Visualization

This module provides utility functions to:
1. Fetch historical OHLCV (Open, High, Low, Close, Volume) data from Binance US using the CCXT library.
2. Load and save datasets (CSV files) to/from local storage.
3. Save and load machine learning models using Keras.
4. Plot distribution of data with a Kernel Density Estimate (KDE) using Seaborn and Matplotlib.

Functions:
    - fetch_data(symbol, timeframe, start_date, end_date): Fetch historical OHLCV data from Binance US.
    - load_data(file_path): Load a CSV file into a pandas DataFrame.
    - save_data(data, file_path): Save a pandas DataFrame to a CSV file.
    - save_model(model, file_path): Save a machine learning model to a specified file path.
    - load_model(file_path): Load a machine learning model from a specified file path.
    - distribution_plot(data, bins=30): Plot the distribution of a given dataset with a KDE.

Dependencies:
    - ccxt: For interacting with the Binance US exchange API.
    - configparser: For reading the configuration file containing API keys and other settings.
    - pandas: For working with data in DataFrame format.
    - seaborn: For statistical data visualization.
    - matplotlib: For plotting the graphs.
    - tensorflow.keras: For saving and loading machine learning models.

Configuration:
    - The module requires a config.ini file containing API credentials for Binance US. The config file should have the following sections:
        [BINANCEUS]
        API_KEY = your_api_key
        SECRET = your_secret_key

    The config file should be located in the 'config' directory one level up from the current script.

Example Usage:
    1. Fetching data:
    >>> df = fetch_data('BTC/USDT', '1h', '2024-01-01 00:00:00', '2024-01-02 00:00:00')
    
    2. Loading and saving data:
    >>> data = load_data('data.csv')
    >>> save_data(data, 'new_data.csv')
    
    3. Saving and loading models:
    >>> save_model(model, 'model.keras')
    >>> model = load_model('model.keras')
    
    4. Plotting distribution:
    >>> distribution_plot(data['price'])

Notes:
    - The fetch_data function fetches data in batches, handling network errors and rate limits gracefully.
    - The model save/load functions assume compatibility with Keras models.
    - The distribution_plot function uses Seaborn's histplot with KDE for data visualization.
"""

import os
import time
import ccxt
import configparser
from pathlib import Path
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from tensorflow.keras.models import load_model as internal_load_model

# Set up the path to the config file
config_path = Path(__file__).resolve().parents[1] / 'config' / 'config.ini'

# Ensure the config file exists
if not config_path.exists():
    raise FileNotFoundError(f"Config file not found at {config_path}.")

# Create a ConfigParser instance and read the config file
config = configparser.ConfigParser()
config.read(config_path)

def fetch_data(symbol, timeframe, start_date, end_date):
    """
    Fetch historical OHLCV (Open, High, Low, Close, Volume) data for a given symbol and timeframe from Binance US.

    Parameters:
    symbol (str): The trading pair symbol (e.g., 'BTC/USD').
    timeframe (str): The timeframe for the OHLCV data (e.g., '1m', '5m', '1h', '1d').
    start_date (str): The start date for fetching data in 'YYYY-MM-DD hh-mm-ss' format.
    end_date (str): The end date for fetching data in 'YYYY-MM-DD hh-mm-ss' format.

    Returns:
    pd.DataFrame: A DataFrame containing the OHLCV data with columns ['timestamp', 'open', 'high', 'low', 'close', 'volume'].
    """

    try:
        # Initialize the exchange with API credentials
        exchange = ccxt.binanceus({
            'apiKey': (config['BINANCEUS']['API_KEY']),
            'secret': (config['BINANCEUS']['SECRET']),
        })
    except Exception as e:
        print(f"Error initializing exchange: {e}")
        return pd.DataFrame()

    limit = 500  # Maximum number of data points to fetch in one request
    start_timestamp = int(pd.Timestamp(start_date).timestamp() * 1000)  # Convert start date to timestamp in milliseconds
    end_timestamp = int(pd.Timestamp(end_date).timestamp() * 1000)  # Convert end date to timestamp in milliseconds

    # Initialize an empty list to store all fetched data
    all_data = []
    
    # Fetch data in batches
    while start_timestamp < end_timestamp:
        try:
            # Fetch OHLCV data from the exchange
            ohlcv_data = exchange.fetch_ohlcv(symbol, timeframe=timeframe, since=start_timestamp, limit=limit)
            
            if not ohlcv_data:
                break  # Exit loop if no data is returned

            # Convert the data to a DataFrame for easier date filtering
            batch_df = pd.DataFrame(ohlcv_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
            batch_df['timestamp'] = pd.to_datetime(batch_df['timestamp'], unit='ms')

            # Filter out data that goes beyond the specified end_date
            batch_df = batch_df[batch_df['timestamp'] < pd.to_datetime(end_date)]
            
            # Check if batch_df is empty before accessing .iloc
            if not batch_df.empty:
                # Append filtered data to all_data list
                all_data.extend(batch_df.values)

                # Print the date range for the batch in human-readable format
                batch_start = batch_df['timestamp'].iloc[0]
                batch_end = batch_df['timestamp'].iloc[-1]
                print(f"Fetched data from {batch_start} to {batch_end}")

                # Update start_timestamp to the last fetched timestamp + 1 ms
                start_timestamp = int(batch_df['timestamp'].iloc[-1].timestamp() * 1000) + 1

                # Stop fetching if the last batch of data has reached the end date
                if batch_df['timestamp'].iloc[-1] >= pd.to_datetime(end_date):
                    break
            else:
                print("No more data within the specified range.")
                break  # Stop fetching if the batch is empty after filtering

            # Sleep between requests based on rate limit to avoid hitting the API rate limit
            time.sleep(exchange.rateLimit / 1000)
        except ccxt.NetworkError as e:
            print(f"Network error: {e}")
            time.sleep(5)  # Wait before retrying
        except ccxt.ExchangeError as e:
            print(f"Exchange error: {e}")
            break
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

    # Convert all_data to a DataFrame
    df_ochlv = pd.DataFrame(all_data, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
    return df_ochlv

def load_data(file_path):
    """
    Load a CSV file from the specified file path.

    Parameters:
    file_path (str): The path to the CSV file to be loaded.

    Returns:
    pd.DataFrame: The loaded dataset.

    Raises:
    FileNotFoundError: If the file does not exist at the specified path.
    """
    if not os.path.exists(file_path):
        raise FileNotFoundError(f"No file found at {file_path}.")
    
    data = pd.read_csv(file_path)
    print(f"Dataset loaded from {file_path}.")
    
    return data

def save_data(data, file_path):
    """
    Save a DataFrame to a CSV file at the specified file path.

    Parameters:
    data (pd.DataFrame): The dataset to be saved.
    file_path (str): The path where the CSV file will be saved.

    Raises:
    ValueError: If the data is None.
    """
    if data is None:
        raise ValueError("No dataset available to save.")
    
    # Ensure the directory exists
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Save the data to the specified path
    data.to_csv(file_path, index=False)
    print(f"Dataset saved to {file_path}.")

def save_model(model, file_path):
    """
    Save the given model to the specified file path.

    Parameters:
    model: The machine learning model to be saved. 
    file_path (str): The path where the model will be saved.

    Raises:
    AttributeError: If the model does not have a `save` method.
    IOError: If there is an issue saving the model to the specified file path.
    """
    model.save(file_path)
    print(f"Model saved to {file_path}.")

def load_model(file_path):
    """
    Load a machine learning model from the specified file path.

    Parameters:
    file_path (str): The path to the model file to be loaded.

    Returns:
    model: The loaded machine learning model.

    Raises:
    IOError: If there is an issue loading the model from the specified file path.
    """
    model = internal_load_model(file_path)
    print(f"Model loaded from {file_path}.")
    return model

def distribution_plot(data, bins=30):
    """
    Plot the distribution of the data with a Kernel Density Estimate (KDE).

    Parameters:
    data (pd.Series or np.ndarray): The data to plot the distribution for.
    bins (int): The number of bins to use for the histogram. Default is 30.

    Returns:
    None
    """
    # Plot distribution with KDE
    sns.histplot(data, kde=True, bins=bins, color='blue')
    plt.title('Distribution with KDE')
    plt.xlabel('Value')
    plt.ylabel('Density')
    plt.show()