import os
import re


def dev_find_textfile():
    base_path = os.getcwd() + "\\data\\stocks"
    for dir in os.listdir(base_path):
        stock_path = os.path.join(base_path, dir)
        print("\n")
        if get_files(stock_path):
            for file in os.listdir(stock_path):
                file_path = os.path.join(stock_path, file)
                with open(file_path, "r", encoding="utf-8") as f:
                    file_text = f.read()
                    text_preprocessor(file_text)
        else:
            print(f"No files in directory: {stock_path}")


def get_files(path):
    fucking_list = ["Alphabet_C", "Arm", "Intel", "Palo_Alto_Networks", "PayPal", "Pfizer"]
    for i in fucking_list:
        if i in path:
            return False
    if os.path.exists(path) and any(os.path.isfile(os.path.join(path, f)) for f in os.listdir(path)):
        return True


def text_preprocessor(text):
    text = get_first_paragraph(text)
    text = remove_initial_line(text)
    text = remove_brackets(text)
    print(text)


def get_first_paragraph(text):
    paragraphs = text.strip().split('\n')

    return paragraphs[0] if paragraphs else ""


def remove_initial_line(text):
    pattern = re.compile(r"\(Updated - [A-Za-z]+ \d{1,2}, \d{4} \d{1,2}:\d{2} [AP]M EDT\)Investing\.com -- ")
    cleaned_text = re.sub(pattern, "", text)

    substrings_to_remove = [
        "Investing.com-- ",
        "Investing.com -- ",
        "Investing.com — "
        "TAIPEI  - ",
        "SAN FRANCISCO--(BUSINESS WIRE)--",
        "SAN FRANCISCO - ",
        "Investing.com - ",
        "U.Today - ",
        ", Inc. ,",
        ", Inc.  ,",
        ",  Inc. ,",
        ",  Inc.  ,",
        " ,  Inc. ,",
    ]

    # Remove each substring
    for substring in substrings_to_remove:
        cleaned_text = cleaned_text.replace(substring, "")

    inc_pattern = re.compile(r"\s*, Inc. ,")
    cleaned_text = re.sub(inc_pattern, "", cleaned_text)

    return cleaned_text


def remove_brackets(text):
    cleaned_text = text.replace("(Reuters)", "")
    nasdaq_pattern_1 = re.compile(r"\(NASDAQ:[^\)]+\)")
    nasdaq_pattern_2 = re.compile(r"\(Nasdaq:[^\)]+\)")
    cleaned_text = re.sub(nasdaq_pattern_1, "", cleaned_text)
    cleaned_text = re.sub(nasdaq_pattern_2, "", cleaned_text)

    return cleaned_text


dev_find_textfile()
