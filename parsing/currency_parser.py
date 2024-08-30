import logging
import bs4 as bs
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from database.models import Stock, StockHistory, DailyStockHistory, MonthlyStockHistory
from database.models import StockNews, SentimentCompound, HistoryToAnalyze
from database.db import get_db
import requests
from requests.exceptions import RequestException
import yfinance as yf


# URL to fetch the most active stocks from Yahoo Finance
CURRENCY_LINK = "https://finance.yahoo.com/most-active/"


# Configure logging to write to both a log file and the console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s:%(levelname)s:%(message)s',
                    handlers=[
                        logging.FileHandler("logs/stock_parser.log"),  # Log to a file
                        logging.StreamHandler()  # Also log to console
                    ]
                    )


def get_page(link=CURRENCY_LINK):
    """
        Fetches and parses a web page.

        Args:
            link (str): URL of the page to fetch. Defaults to the Yahoo Finance active stocks page.

        Returns:
            BeautifulSoup object if successful, None otherwise.
    """
    try:
        logging.info("Opening the web page...")
        response = requests.get(link)
        response.raise_for_status()
        soup = bs.BeautifulSoup(response.text, 'html.parser')
        return soup
    except RequestException as e:
        logging.error(f"Failed to retrieve the page: {e}")
        return None


def get_company_name(row):
    """
        Extracts the company name from a table row.

        Args:
            row (BeautifulSoup object): A table row element containing stock data.

        Returns:
            str: The company name, or None if extraction fails.
    """
    try:
        company_name = row.find('td', attrs={'class': 'Va(m) Ta(start) Px(10px) Fz(s)'}).text
        company_name = company_name.replace(', Inc.', '')
        company_name = company_name.replace(' Inc.', '')
        return company_name
    except AttributeError as e:
        logging.error(f"Failed to get company name: {e}")
        return None


def get_stock_name(row):
    """
        Extracts the stock symbol from a table row.

        Args:
            row (BeautifulSoup object): A table row element containing stock data.

        Returns:
            str: The stock symbol, or None if extraction fails.
    """
    try:
        return row.find('a', attrs={"data-test": "quoteLink"}).text
    except AttributeError as e:
        logging.error(f"Failed to get stock name: {e}")
        return None


def get_currencies(page):
    """
        Extracts stock data from the provided web page.

        Args:
            page (BeautifulSoup object): The parsed HTML page containing stock data.

        Returns:
            dict: A dictionary containing stock data for each company.
    """
    try:
        logging.info("Page loaded successfully. Parsing content...")

        rows = page.find('tbody').find_all('tr')
        if not rows:
            raise ValueError("No rows found in the table.")

        companies_dict = {}
        for row in rows:
            company_name = get_company_name(row)
            if not company_name:
                continue
            change_cell = row.find("span").text
            change_prc_cell = row.find("td", attrs={"aria-label": "% Change"}).text
            growth = True if change_cell[0] == "+" else False

            stock_name = get_stock_name(row)
            if not stock_name:
                continue
            stock_history = yf.Ticker(stock_name).history()

            companies_dict[company_name] = {
                "last": float(round(stock_history["Close"].iloc[-1], 2)),
                "high": float(round(stock_history["High"].iloc[-1], 2)),
                "low": float(round(stock_history["Low"].iloc[-1], 2)),
                "vol": float(round(stock_history["Volume"].iloc[-1]/1000000, 3)),
                "change": change_cell[1:],
                "change_pct": change_prc_cell[1:-1],
                "growth": growth
            }
        logging.info(f"Fetched data for {len(companies_dict)} companies.")
        return companies_dict

    except Exception as e:
        logging.error(f"Error fetching currencies: {e}")
        return {}


def get_historical_data(page, history_period):
    """
        Fetches historical data for stocks listed on the provided page.

        Args:
            page (BeautifulSoup object): The parsed HTML page containing stock data.
            history_period (dict): Specifies the period and interval for fetching historical data.

        Returns:
            dict: A dictionary containing historical stock data for each company.
    """
    try:
        logging.info("Page for historical data loaded successfully. Parsing content...")

        rows = page.find('tbody').find_all('tr')
        if not rows:
            raise ValueError("No rows found in the table.")

        company_history = {}
        for row in rows:
            stock_name = get_stock_name(row)
            company_name = get_company_name(row)
            ticker = yf.Ticker(stock_name)
            hist_data = ticker.history(period=history_period["period"], interval=history_period["interval"])
            historical_prices = []

            for date, row in hist_data.iterrows():
                historical_prices.append({
                    "title": company_name,
                    "open": float(round(row["Open"], 2)),
                    "high": float(round(row["High"], 2)),
                    "low": float(round(row["Low"], 2)),
                    "close": float(round(row["Close"], 2)),
                    "volume": float(round(row["Volume"], 2)),
                    "date": date,
                })
            company_history[company_name] = historical_prices
        return company_history

    except Exception as e:
        logging.error(f"Error fetching currencies: {e}")
        return {}


def update_companies(page):
    """
        Updates the Stock table in the database with the latest data.

        Args:
            page (BeautifulSoup object): The parsed HTML page containing stock data.
    """
    db = next(get_db())
    try:
        logging.info("Clearing the Stock table...")

        db.query(Stock).delete()
        db.commit()

        db.execute(text("ALTER SEQUENCE stocks_id_seq RESTART WITH 1"))
        db.commit()

        logging.info("Fetching currencies...")
        companies_dict = get_currencies(page)
        if not companies_dict:
            logging.error("Failed to fetch company data")
            raise Exception("Failed to fetch company data")

        stocks = []
        for name, value in companies_dict.items():
            stock = Stock(title=name,
                          last=value['last'],
                          high=value['high'],
                          low=value['low'],
                          volume=value['vol'],
                          change=value['change'],
                          change_pct=value['change_pct'],
                          growth=value['growth'])
            stocks.append(stock)

        db.bulk_save_objects(stocks)
        db.commit()
        logging.info("Companies updated successfully.")

    except (SQLAlchemyError, Exception) as e:
        db.rollback()
        logging.error(f"Error updating companies: {e}")

    finally:
        db.close()


def update_companies_history(history_period, page):
    """
        Updates the historical stock data in the database.

        Args:
            history_period (dict): Specifies the model and sequence details for different historical periods.
            page (BeautifulSoup object): The parsed HTML page containing stock data.
    """
    db = next(get_db())
    try:
        logging.info("Clearing the Stock-History table...")

        db.query(history_period["model"]).delete()
        db.commit()

        db.execute(text(f"ALTER SEQUENCE {history_period['id']} RESTART WITH 1"))
        db.commit()

        logging.info("Fetching currencies...")
        companies_dict = get_historical_data(page, history_period)
        if not companies_dict:
            logging.error("Failed to fetch company data")
            raise Exception("Failed to fetch company data")

        stocks_hist = []
        for name, values in companies_dict.items():
            for value in values:
                stock_hist = history_period["model"](title=name,
                                                     open=value['open'],
                                                     high=value['high'],
                                                     low=value['low'],
                                                     close=value['close'],
                                                     volume=value['volume'],
                                                     date=value['date'])
                stocks_hist.append(stock_hist)

        db.bulk_save_objects(stocks_hist)
        db.commit()
        logging.info("Companies history updated successfully.")

    except (SQLAlchemyError, Exception) as e:
        db.rollback()
        logging.error(f"Error updating companies history: {e}")

    finally:
        db.close()


def clear_dependencies():
    """
        Clears data in related dependency tables (StockNews and SentimentCompound) in the database.
    """
    db = next(get_db())
    try:
        logging.info("Clearing dependencies...")
        db.query(SentimentCompound).delete()
        db.commit()

        db.execute(text("ALTER SEQUENCE stock_compound_id_seq RESTART WITH 1"))
        db.commit()

        db.query(StockNews).delete()
        db.commit()

        db.execute(text("ALTER SEQUENCE stock_news_id_seq RESTART WITH 1"))
        db.commit()

        logging.info("Dependencies cleared successfully.")
    except Exception as e:
        db.rollback()
        logging.error(f"Failed to clear dependencies: {e}")

    finally:
        db.close()


def start_parsing():
    """
        Initiates the process to clear dependencies and update companies' data.
    """
    clear_dependencies()
    page = get_page()
    if page:
        update_companies(page=page)
    else:
        logging.error("Failed to start parsing due to page load failure.")


def start_parsing_history():
    """
        Initiates the process to fetch and update historical stock data for different periods (year, month, day).
    """
    history = {
        "year": {"period": "1y", "interval": "1d", "model": StockHistory, "id": "stocks_history_id_seq"},
        "month": {"period": "1mo", "interval": "30m", "model": MonthlyStockHistory, "id": "monthly_history_id_seq"},
        "day": {"period": "1d", "interval": "5m", "model": DailyStockHistory, "id": "daily_history_id_seq"},
        "2_years": {"period": "2y", "interval": "1d", "model": HistoryToAnalyze, "id": "analyze_history_id_seq"}
    }
    page = get_page()
    update_companies_history(history["year"], page=page)
    update_companies_history(history["month"], page=page)
    update_companies_history(history["day"], page=page)
    update_companies_history(history["2_years"], page=page)
