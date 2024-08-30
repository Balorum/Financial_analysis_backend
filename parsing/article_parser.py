import logging
import bs4 as bs
import requests
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from random import choice
import yfinance as yf
from database.db import get_db
from database.models import StockNews, Stock, SentimentCompound
from parsing import article_analyzer


# Configure logging to write to both a log file and the console
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s',
                    handlers=[
                        logging.FileHandler("logs/article_parser.log"),  # Log to a file
                        logging.StreamHandler()  # Also log to console
                    ]
                    )


# Different user-agent headers to mimic various browsers for web scraping
header_1 = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/71.0.3578.98 Safari/537.36'}
header_2 = {'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/102.0.0.0 Safari/537.36"}
header_3 = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.106 Safari/537.36 OPR/38.0.2220.41"}
header_4 = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/51.0.2704.103 Safari/537.36"}
header_5 = {"User-Agent": "Mozilla/5.0 (Linux; U; Linux i674 x86_64; en-US) AppleWebKit/600.12 (KHTML, like Gecko) Chrome/53.0.2954.236 Safari/602"}


# List of headers to randomly choose from to avoid being blocked during scraping
HEADERS = [header_1, header_2, header_3, header_4, header_5]


def get_companies_news():
    """
        Fetches news articles for all companies from Yahoo Finance.

        Returns:
            dict: A dictionary mapping stock symbols to a list of article links.
    """
    db = next(get_db())  # Get a database session
    logging.info(f"Query the database to get all current stocks...")
    stocks = db.query(Stock).all()  # Fetch all stock entries from the database
    if not stocks:
        logging.error("No stocks found.")
    news_dict = {}

    for stock in stocks:
        try:
            news = yf.Ticker(stock.title).get_news()  # Get news articles for the stock
            article_list = []
            for article in news:
                article_list.append(article["link"])  # Collect article links

            news_dict[stock.title] = article_list
        except Exception as e:
            logging.error(f"Error fetching news for {stock.title}: {e}")

    return news_dict


def fetch_article_content():
    """
        Fetches content of the news articles, analyzes them, and saves the results to the database.
    """
    news_dict = get_companies_news()
    articles_dict = {}
    for company, links in news_dict.items():
        logging.info(f"Analyzing company {company} started")
        titles_list = []
        links_list = []
        summary_list = []
        rating_list = []
        for news_link in links:
            try:
                # Request each news article with a random header to avoid blocking
                response_news = requests.get(news_link, headers=choice(HEADERS), timeout=40)
                soup_news = bs.BeautifulSoup(response_news.text, 'html.parser')

                # Skip articles with certain classes
                if soup_news.find('a', attrs={"class": "caas-readmore caas-readmore-collapse"}):
                    continue

                # Locate the main content of the article
                article_div = soup_news.find("div", attrs={
                        "class": "morpheusGridBody col-neofull-offset-3-span-8 col-neolg-offset-3-span-8 col-neomd-offset-1-span-6 col-neosm-offset-2-span-4"})
                if not article_div:
                    continue

                # Extract paragraphs and check if there is sufficient content
                paragraphs = article_div.find_all('p')
                if len(paragraphs) < 2:
                    continue

                # Analyze the article to get a summary and rating
                summary, rating = analyze_articles(company, paragraphs)

                # Extract and store the article title, link, summary, and rating
                title = soup_news.find('h1', attrs={"id": "caas-lead-header-undefined"})
                if title:
                    titles_list.append(title.text)
                    links_list.append(news_link)
                    summary_list.append(summary)
                    rating_list.append(rating)
            except Exception as e:
                logging.error(f"While analyzing company {company} on {news_link} got exception {e}")
        logging.info(f"Analyzing company {company} finished")

        # Normalize the company name for consistent storage
        company_name = normalize_company_name(company)
        articles_dict[company_name] = [titles_list, links_list, summary_list, rating_list]

    # Save the analyzed articles and their sentiment compounds
    save_compound(articles_dict)
    save_articles_news(articles_dict)


def calc_compound(rating_list):
    """
        Calculates the compound sentiment probabilities for a list of ratings.

        Args:
            rating_list (list): A list of ratings with probability metrics.

        Returns:
            tuple: Decrease and increase probability averages.
    """
    rise = 0
    fall = 0
    inform = 0
    for news_rate in rating_list:
        rise = rise + (news_rate["Increase Probability"] * news_rate["Informativeness"])
        fall = fall + (news_rate["Decrease Probability"] * news_rate["Informativeness"])
        inform = inform + news_rate["Informativeness"]

    # Calculate the probability of stock prices falling or rising
    fall_prob = fall/inform
    rise_prob = rise/inform
    return fall_prob, rise_prob


def save_compound(article_dict):
    """
        Saves the sentiment compound data to the database.

        Args:
            article_dict (dict): Dictionary of analyzed articles with sentiment data.
    """
    db = next(get_db())
    try:

        # Clear existing sentiment compound data
        db.query(SentimentCompound).delete()
        db.commit()

        db.execute(text("ALTER SEQUENCE stock_compound_id_seq RESTART WITH 1"))  # Reset sequence
        db.commit()

        logging.info("Updating stock compound...")
        stock_compounds = []
        for company, values_list in article_dict.items():
            stock = db.query(Stock).filter_by(title=company).first()
            if stock:

                # Calculate the compound sentiment probabilities
                fall_prob, rise_prob = calc_compound(values_list[3])
                compound = SentimentCompound(
                    stock_id=stock.id,
                    fall_probability=round(fall_prob, 2),
                    rise_probability=round(rise_prob, 2),

                )
                stock_compounds.append(compound)
            else:
                logging.warning(f"Stock '{company}' not found in the Stock table")

        db.bulk_save_objects(stock_compounds)  # Save all compounds in bulk
        db.commit()

        logging.info("Stock compounds updated successfully.")
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Failed to update stock compounds: {e}")
    finally:
        db.close()


def normalize_company_name(company):
    """
        Normalizes the company name by removing suffixes.

        Args:
            company (str): The original company name.

        Returns:
            str: Normalized company name.
    """
    company_name = company.replace(', Inc.', '')
    company_name = company_name.replace(' Inc.', '')

    return company_name


def analyze_articles(company, rows):
    """
        Analyzes the content of an article and returns a summary and sentiment rating.

        Args:
            company (str): The company name.
            rows (list): List of paragraphs from the article.

        Returns:
            tuple: Summary and rating of the article.
    """
    article = ""
    for row in rows:
        article += row.text  # Concatenate all paragraph texts into a single article string

    # Use an external analyzer to generate a summary and sentiment rating for the article
    summary, rating = article_analyzer.main(article, company)
    return summary, rating


def save_articles_news(news_dict):
    """
        Saves the analyzed news articles to the database.

        Args:
            news_dict (dict): Dictionary of articles and their related data.
    """
    db = next(get_db())
    try:
        logging.info("Delete previous news...")
        db.query(StockNews).delete()  # Delete previous news entries
        db.commit()

        db.execute(text("ALTER SEQUENCE stock_news_id_seq RESTART WITH 1"))  # Reset sequence
        db.commit()

        logging.info("Updating stock news...")

        stock_news = []
        for company, news_list in news_dict.items():
            for title, link, summary, rating in zip(news_list[0], news_list[1], news_list[2], news_list[3]):
                stock = db.query(Stock).filter_by(title=company).first()
                if stock:

                    # Create a new StockNews entry for each article
                    one_news = StockNews(
                        stock_id=stock.id,
                        title=title,
                        link=link,
                        summary=summary,
                        decrease=rating["Decrease Probability"],
                        increase=rating["Increase Probability"],
                        informativeness=rating["Informativeness"]
                    )
                    stock_news.append(one_news)
                else:
                    logging.warning(f"Stock '{company}' not found in the Stock table")

        db.bulk_save_objects(stock_news)  # Bulk save all news entries
        db.commit()

        logging.info("Stock news updated successfully.")
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Failed to update stock news: {e}")
    finally:
        db.close()


def clear_news_db():
    """
        Clears the news data from the StockNews table in the database.
    """
    db = next(get_db())
    try:
        logging.info("Trying to delete stock news...")
        db.query(StockNews).delete()  # Delete all news entries
        db.commit()

        db.execute(text("ALTER SEQUENCE stock_news_id_seq RESTART WITH 1"))  # Reset sequence
        db.commit()
        logging.info("Stock news deleted successfully.")
    except SQLAlchemyError as e:
        db.rollback()
        logging.error(f"Failed to delete stock titles: {e}")
