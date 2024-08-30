import nltk
import re
from time import sleep
import logging

# Import necessary modules from NLTK
from nltk.corpus import stopwords
nltk.download('vader_lexicon') # Download required lexicons for sentiment analysis
nltk.download('punkt')  # Download the punkt tokenizer models
nltk.download('stopwords')  # Download the stopwords corpus

import vertexai
from vertexai.generative_models import GenerativeModel


# Set up logging to file and console for debugging and information
logging.basicConfig(
    level=logging.INFO,  # Set log level to INFO, change to DEBUG for more detailed output
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("logs/article_analysis.log"),  # Write logs to a file
        logging.StreamHandler()  # Print logs to console
    ]
)

# Initialize Vertex AI for model inference
project_id = "phonic-obelisk-431915-c8"
vertexai.init(project=project_id, location="europe-west2")

# Placeholder for AI models that will be created
MODELS = []

# Load stopwords from NLTK for filtering out common words
stop_words = set(stopwords.words("english"))

# Regular expressions for cleaning and extracting information from text
SUPERFLUOUS_PATTERN_1 = re.compile(r'\(\w+\)')  # Matches single-word patterns in parentheses
SUPERFLUOUS_PATTERN_2 = re.compile(r'\(NASDAQ: \w+\)')  # Matches NASDAQ stock symbols in parentheses
PUNCTUATION_PATTERN = re.compile(r'[^\w\s]')  # Matches non-alphanumeric characters
FORECAST_PATTERN_1 = re.compile(r'\(decrease (\d+%) \| increase (\d+%)\)')  # Matches decrease/increase forecast format
FORECAST_PATTERN_2 = re.compile(r'\(increase (\d+%) \| decrease (\d+%)\)')  # Matches increase/decrease forecast format
INFORMATIVENESS_PATTERN = re.compile(r'\(informativeness: (\d+%)\)')  # Matches informativeness percentage pattern


def create_models():
    """
        Initializes and returns a list of generative AI models for content generation.

        Returns:
            list: A list containing initialized GenerativeModel instances.
    """
    logging.info("Creating AI models...")
    model_1 = GenerativeModel("gemini-1.5-flash-001")
    model_2 = GenerativeModel("gemini-1.5-flash-001")
    model_3 = GenerativeModel("gemini-1.5-flash-001")
    return [model_1, model_2, model_3]


def delete_superfluous(article):
    """
        Removes superfluous patterns like single-word parentheses and NASDAQ symbols from the article.

        Args:
            article (str): The article text.

        Returns:
            str: The cleaned article text.
    """
    article = SUPERFLUOUS_PATTERN_1.sub('', article)
    article = SUPERFLUOUS_PATTERN_2.sub('', article)
    return article


def delete_punctuation(article):
    """
        Removes all punctuation from the article.

        Args:
            article (str): The article text.

        Returns:
            str: The article text without punctuation.
    """
    return PUNCTUATION_PATTERN.sub('', article)


def sentence_tokenization(sentence):
    """
        Tokenizes a given sentence into words.

        Args:
            sentence (str): A sentence to tokenize.

        Returns:
            list: A list of words in the sentence.
    """
    article_word_list = nltk.tokenize.word_tokenize(sentence)
    return article_word_list


def article_tokenization(article):
    """
        Tokenizes the entire article into individual sentences.

        Args:
            article (str): The article text.

        Returns:
            list: A list of sentences in the article.
    """
    sentences = nltk.tokenize.sent_tokenize(article)
    return sentences


def delete_stop_words(article_list):
    """
        Removes common stopwords from the list of words in the article.

        Args:
            article_list (list): A list of words in the article.

        Returns:
            list: A list of words without stopwords.
    """
    global stop_words
    processed_article = [word for word in article_list if word.lower() not in stop_words]
    return processed_article


def request_processing(request):
    """
        Sends a request to an AI model for content analysis, with retries in case of failures.

        Args:
            request (str): The text request to send for analysis.

        Returns:
            str: The AI model's response.
    """
    global MODELS

    if not MODELS:
        MODELS = create_models()  # Create models if they haven't been initialized

    max_retries = 6
    delay = 10
    backoff_factor = 5

    for attempt in range(max_retries):
        model = MODELS.pop()  # Take a model from the pool
        logging.info(f"Attempt {attempt + 1}: Sending request to AI model for analysis...")
        try:
            response = model.generate_content(request)
            if response:
                sleep(10)  # Pause to avoid rate-limiting issues
                logging.info("AI analysis completed.")
                return response  # Return response if successful
        except Exception as e:
            if '429' in str(e):  # Handle rate-limiting errors
                logging.warning(f"Received 429 Too Many Requests. Retrying after {delay} seconds...")
                sleep(delay)
                delay += backoff_factor
                MODELS.append(model)  # Re-append the model if it failed
            else:
                logging.error(f"Error occurred: {e}")
                raise

    logging.error("Max retries reached. Unable to complete the AI analysis.")
    return None


def text_processing(article_text):
    """
        Processes the text of an article by cleaning, tokenizing, and removing stopwords.

        Args:
            article_text (str): The article text.

        Returns:
            str: The processed article text.
    """
    logging.info("Processing article text...")
    words_list = []
    sentences_list = []
    sentences = article_tokenization(article_text)  # Tokenize article into sentences
    for sentence in sentences:
        sentence = delete_superfluous(sentence)  # Remove unwanted patterns
        sentence = delete_punctuation(sentence)  # Remove punctuation
        tokenized_sentence = sentence_tokenization(sentence)  # Tokenize sentence into words
        without_base_sw = delete_stop_words(tokenized_sentence)  # Remove stopwords
        words_list.append(without_base_sw)
    for word_list in words_list:
        sentence = ' '.join(word_list)  # Reconstruct sentences from words
        sentence = sentence.capitalize()
        sentence = re.sub(r'([.!?])(\w)', r'\1 \2', sentence)  # Add spacing after punctuation
        sentences_list.append(sentence)
    processed_article = ". ".join(sentences_list)  # Join sentences into a processed article
    return processed_article


def ai_analyzer(article, company_name):
    """
        Constructs a request for AI analysis and sends it to the model.

        Args:
            article (str): The processed article text.
            company_name (str): The name of the company being analyzed.

        Returns:
            str: The AI model's response.
    """
    request = (f"I have several financial articles about {company_name}. I want you to analyze each one in turn "
               f"and provide the result in the form of: 3 sentences that best describe what the article is about, "
               f"and also I want you to provide a forecast based on this news, with what chance the stock price will "
               f"go up and with what chance it will go down in the format: '(decrease 30% | increase 70%)' - the total"
               f" should be 100%. And also how useful is this article for predicting the rise/fall of a stock in the "
               f"format '(Informativeness: 50%)'. Here is one of the articles: \n\n{article}")

    return request_processing(request).text


def get_rate(summary):
    """
        Extracts forecast probabilities and informativeness from the AI-generated summary.

        Args:
            summary (str): The AI-generated summary of the article.

        Returns:
            dict: A dictionary containing probabilities for stock increase/decrease and informativeness.
    """
    logging.info("Extracting forecast and informativeness from AI summary...")

    forecast_pattern_1 = re.compile(r'\(decrease (\d+%) \| increase (\d+%)\)')
    forecast_pattern_2 = re.compile(r'\(increase (\d+%) \| decrease (\d+%)\)')
    informativeness_pattern = re.compile(r'\(informativeness: (\d+%)\)')

    lower_summary = summary.lower()  # Convert summary to lowercase
    forecasts = forecast_pattern_1.findall(lower_summary)  # Find forecast patterns
    if not forecasts:  # Check if patterns are found
        swap = forecast_pattern_2.findall(lower_summary)
        if swap:
            if len(swap[0]) >= 2:
                forecasts = [(swap[0][1], swap[0][0])]  # Swap forecast probabilities if pattern is reversed
        if not swap:
            forecasts = ["50%", "50%"]  # Default to 50-50 if no patterns found
    informativeness = informativeness_pattern.findall(lower_summary)
    if not informativeness:
        informativeness = 50  # Default informativeness if not found
    else:
        informativeness = int(informativeness[0].replace('%', ''))

    decrease = int(forecasts[0][0].replace('%', ''))
    increase = int(forecasts[0][1].replace('%', ''))

    logging.info(f"Informativeness: {informativeness}, Decrease: {decrease}%, Increase: {increase}%")

    data = {
        'Decrease Probability': decrease,
        'Increase Probability': increase,
        'Informativeness': informativeness,
    }
    return data


def response_processing(response):
    """
        Cleans the AI-generated response by removing unnecessary patterns.

        Args:
            response (str): The AI-generated response text.

        Returns:
            str: The cleaned response text.
    """
    logging.info("Processing AI response...")
    patterns_to_remove = [
        r"\*\*.*?\*\*|##.*?##', '"  # Patterns to remove
        r"\n\s*\n', '\n\n",
        r"##.*",
        r'\(.*?\)',
        r'\b\d+\.',
        r'\*',
    ]

    for pattern in patterns_to_remove:
        response = re.sub(pattern, '', response)  # Remove unwanted patterns
    response = re.sub(r'\n+', '\n', response)  # Normalize new lines
    response = response.strip()  # Remove leading/trailing whitespace
    return response


def main(article, company_name):
    """
        Main function to process an article, send it for AI analysis, and extract the results.

        Args:
            article (str): The article text.
            company_name (str): The name of the company being analyzed.

        Returns:
            tuple: A tuple containing the cleaned article summary and analysis rating.
    """
    processed_article = text_processing(article)  # Pre-process the article
    summary = ai_analyzer(processed_article, company_name)  # Send to AI for analysis
    rating = get_rate(summary)  # Extract rating information
    ready_article = response_processing(summary)  # Clean the AI response
    return ready_article, rating
