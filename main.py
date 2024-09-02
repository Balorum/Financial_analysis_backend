from parsing import article_parser, currency_parser
from database.models import StockHistory, MonthlyStockHistory, DailyStockHistory, HistoryToAnalyze

import logging
import warnings
warnings.simplefilter(action='ignore', category=FutureWarning)



history = {
        "year": {"period": "1y", "interval": "1d", "model": StockHistory, "id": "stocks_history_id_seq"},
        "month": {"period": "1mo", "interval": "30m", "model": MonthlyStockHistory, "id": "monthly_history_id_seq"},
        "day": {"period": "1d", "interval": "5m", "model": DailyStockHistory, "id": "daily_history_id_seq"},
        "2_years": {"period": "2y", "interval": "1d", "model": HistoryToAnalyze, "id": "analyze_history_id_seq"}
    }


def start_analyze():
    page = currency_parser.get_page()
    if not page:
        logging.error("Failed to start parsing due to page load failure.")

    # Get currently currencies
    companies_dict = currency_parser.get_currencies(page)

    # Financial news analysis
    companies_news = article_parser.get_companies_news(companies_dict)
    articles_dict = article_parser.fetch_article_content(companies_news)

    # Save currencies
    currency_parser.clear_dependencies()
    currency_parser.update_companies(companies_dict)

    # Get and save historical currencies
    for period, params in history.items():
        historical_dict = currency_parser.get_historical_data(page, params)
        currency_parser.update_companies_history(params, historical_dict)

    # Save the analyzed articles and their sentiment compounds
    article_parser.save_compound(articles_dict)
    article_parser.save_articles_news(articles_dict)


if __name__ == '__main__':
    start_analyze()
