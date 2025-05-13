import pandas as pd
import requests
from duckduckgo_search import DDGS 
from duckduckgo_search.exceptions import DuckDuckGoSearchException

from newspaper import Article
import time
import csv
import re

from dotenv import load_dotenv
load_dotenv()

import os
API_KEY = os.getenv("GOOGLE_API_KEY")
CX_ID = os.getenv("GOOGLE_CX_ID")



def search_duckduckgo(query, max_results=5, retries=3, wait_seconds=30):
    for attempt in range(retries):
        try:
            with DDGS() as ddgs:
                results = ddgs.text(query, max_results=max_results)
                time.sleep(1)  # polite delay between normal searches
                return [r['href'] for r in results if 'href' in r]
        except DuckDuckGoSearchException as e:
            print(f"[RateLimit] Attempt {attempt+1}/{retries} for query: '{query}'")
            if attempt < retries - 1:
                print(f"⏳ Waiting {wait_seconds} seconds before retrying...")
                time.sleep(wait_seconds)
                return None
            else:
                print("❌ Failed after max retries.")
                return []
    return None

def search_google(query, max_results=5, retries=3, wait_seconds=2, backoff_factor=2):
    url = "https://www.googleapis.com/customsearch/v1"
    params = {
        "q": query,
        "key": API_KEY,
        "cx": CX_ID,
        "num": max_results,
    }

    for attempt in range(retries):
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            # print(f'sample resonpse for {query} ',data)
            return [item["link"] for item in data.get("items", [])]
        except Exception as e:
            print(f"[Attempt {attempt+1}/{retries}] Error: {e}")
            if attempt < retries - 1:
                delay = wait_seconds * (backoff_factor ** attempt)
                print(f"⏳ Retrying in {delay} seconds...")
                time.sleep(delay)
                return None
            else:
                print("❌ Giving up after max retries.")
                return []
    return None


def extract_article_text(url):
    try:
        article = Article(url)
        article.download()
        article.parse()
        text = article.text
        # Remove empty lines, trim whitespace
        text = re.sub(r'\n\s*\n+', '\n', text)
        text = re.sub(r'\s+', ' ', text)
        return text.strip()
    except:
        return ""

def is_valid_summary(text):
    # Must have at least 300 characters and 2 sentences
    if len(text) < 300:
        return False
    if text.count('.') < 2:
        return False
    return True

def generate_queries(company):
    queries = [
            f"{company} line of business",
            f"{company} industry",
            f"{company} company summary",
        ]
    return queries

def get_all_urls(queries):
    all_urls=set()
    for q in queries:
        print('searching ',q,' ...')
        # urls = search_duckduckgo(q,max_results=4)
        urls = search_google(q,max_results=4)
        all_urls.update(urls)
        time.sleep(1)
    return list(all_urls)

def enrich_companies_with_web_data(input_csv, output_csv):
    df = pd.read_csv(input_csv, delimiter=';')
    processed_rows=0
    total_rows= len(df)
    try:
        existing_df = pd.read_csv(output_csv, delimiter=';')
        existing_companies = set(existing_df['Company Name'])
    except FileNotFoundError:
        existing_df = pd.DataFrame()
        existing_companies = set()

    for index, row in df.iterrows():
        print('current progress ',(processed_rows/total_rows)*100,'%')
        company = row['Company Name']
        category= row['Category']
        if company in existing_companies:
            print(f"Skipping: {company} (already processed)")
            processed_rows+=1
            continue

        print(f"🔍 Searching: {company}")
        
        queries = generate_queries(company)
        urls=get_all_urls(queries)        
        combined_text = ""
        for url in urls:
            text = extract_article_text(url)
            if is_valid_summary(text):
                combined_text += text[:2000] + "\n---\n"
            time.sleep(1)

        if len(combined_text)==0:
            print(f"didn't found info for {company}")
            continue

        if not combined_text.strip():
            print(f"⚠️ No valid summary found for {company}")
            continue

        summary = {
            'Company Name': company,
            'Search Summary': combined_text.strip(),
            'Category': category
        }

        new_df = pd.DataFrame([summary])
        new_df.to_csv(output_csv, mode='a', sep=';', index=False, quoting=csv.QUOTE_ALL, header=False)

        print(f"✅ Updated {output_csv} with: {company}")
        existing_companies.add(company)
        processed_rows+=1
