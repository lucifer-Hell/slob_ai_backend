import pandas as pd
import os , sys
import torch
import torch.nn.functional as F
from transformers import AutoTokenizer, AutoModelForSequenceClassification,AutoConfig

# === Model + Tokenizer Setup ===
import os
MODEL_PATH = os.path.abspath(os.path.join(os.path.dirname(__file__), "./model/slobp"))
LABELS_CSV =os.path.abspath(os.path.join(os.path.dirname(__file__), "./data/CATEGORIES.csv"))

print("Current working directory:", os.getcwd())

DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")

config = AutoConfig.from_pretrained(MODEL_PATH, local_files_only=True)
tokenizer = AutoTokenizer.from_pretrained(MODEL_PATH,config=config)
model = AutoModelForSequenceClassification.from_pretrained(MODEL_PATH,config=config).to(DEVICE)
model.eval()

df = pd.read_csv(LABELS_CSV, delimiter=",")
LABELS = sorted(df["Category"].dropna().unique().tolist())

LABELS2ID= { label: i for i , label in enumerate(LABELS)}
ID2LABELS={i : label for i , label in enumerate(LABELS)}

# === Import DuckDuckGo logic ===
from utils.crawler import generate_queries, get_all_urls, extract_article_text, is_valid_summary

# === LOB Classifier ===
def classify_lob_from_text(company, summary):
    text = f"Company Name: {company}\n\nSearch Summary: {summary}"
    inputs = tokenizer(text, return_tensors="pt", truncation=True, padding=True, max_length=2048)
    inputs = {k: v.to(DEVICE) for k, v in inputs.items()}
    with torch.no_grad():
        outputs = model(**inputs)
        logits = outputs.logits
        probs = F.softmax(logits, dim=1)
        pred = torch.argmax(probs, dim=1).item()
    return ID2LABELS.get(pred, "UN_CLASSIFIED")

# === Sample CSV for Download ===
SAMPLE_PATH = "sample_suppliers.csv"
if not os.path.exists(SAMPLE_PATH):
    pd.DataFrame({'supplier_name': ['Infosys', 'Walmart', 'Bosch']}).to_csv(SAMPLE_PATH, index=False)

# === File Processing Function ===
def process_file(file):
    df = pd.read_csv(file.name)
    return process_df(df)

def process_df(companies):
    # Convert to DataFrame if it's a list of dicts
    if isinstance(companies, list):
        companies = pd.DataFrame(companies)

    enriched_data = []
    for name in companies['company_name']:
        queries = generate_queries(name)
        urls = get_all_urls(queries)

        summary_text = ""
        for url in urls:
            article = extract_article_text(url)
            if is_valid_summary(article):
                summary_text = article
                break

        if not summary_text:
            summary_text = "No valid summary found."
            enriched_data.append({
                "company_name": name,
                "predicted_line_of_business": "NO DATA FOUND ONLINE"
            })
            continue

        predicted_lob = classify_lob_from_text(name, summary_text)

        enriched_data.append({
            "company_name": name,
            "predicted_line_of_business": predicted_lob
        })

    return enriched_data
