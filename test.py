# from database.db import get_db
# from database.models import HistoryToAnalyze
#
#
# db = next(get_db())  # Get a database session
# stocks = db.query(HistoryToAnalyze).all()
#
# for i in stocks:
#     print(i.title)

from parsing import currency_parser, article_parser

# currency_parser.start_parsing_history()
page = currency_parser.get_page()
companies_dict = currency_parser.get_currencies(page)

companies_dict = list(companies_dict.keys())

print(companies_dict)
print(type(companies_dict))