# File: my-journalist-project/my_framework/src/my_framework/apps/style_guru.py

import os
import re
import time
from pathlib import Path
import numpy as np
from newspaper import Article
from dotenv import load_dotenv
import requests
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from ..models.openai import ChatOpenAI
from ..core.schemas import HumanMessage, SystemMessage
from . import rules

load_dotenv()

DATA_DIR = Path("data")
RAW_DIR = DATA_DIR / "raw"
RAW_DIR.mkdir(parents=True, exist_ok=True)

RSS_URLS = [
    "https://www.intellinews.com/feed/atom?type=full_text",
    "https://www.intellinews.com/feed?client=bloomberg"
]
START_URL = "https://intellinews.com/"
ARTICLE_PATTERN = re.compile(r"-\d{6}/")

class AdvancedNeuralAgent:
    """
    NN for IntelliNews style scoring.
    Input: feature vector (text style metrics)
    Output: scalar style score
    """

    def __init__(self, input_size: int, hidden=[64, 32], lr=1e-3):
        self.lr = lr
        self.layers = []
        layer_sizes = [input_size] + hidden + [1]
        for i in range(len(layer_sizes)-1):
            fan_in, fan_out = layer_sizes[i], layer_sizes[i+1]
            limit = np.sqrt(6.0 / (fan_in + fan_out))
            self.layers.append({
                "w": np.random.uniform(-limit, limit, (fan_in, fan_out)),
                "b": np.zeros((1, fan_out)),
                "mw": np.zeros((fan_in, fan_out)),
                "mb": np.zeros((1, fan_out)),
            })

    def _relu(self, x): return np.maximum(0, x)
    def _drelu(self, x): return (x > 0).astype(float)

    def forward(self, X):
        self.a = [X]; self.z = []
        for i, l in enumerate(self.layers):
            z = np.dot(self.a[-1], l["w"]) + l["b"]
            self.z.append(z)
            if i < len(self.layers)-1:
                self.a.append(self._relu(z))
            else:
                self.a.append(z)  # linear output
        return self.a[-1]

    def train(self, X, y, epochs=100, batch_size=16):
        y = y.reshape(-1, 1)
        for ep in range(epochs):
            idx = np.random.permutation(len(X))
            Xs, ys = X[idx], y[idx]
            losses = []
            for i in range(0, len(Xs), batch_size):
                xb, yb = Xs[i:i+batch_size], ys[i:i+batch_size]
                out = self.forward(xb)
                dz = (out - yb) / len(xb)
                for li in reversed(range(len(self.layers))):
                    l = self.layers[li]
                    a_prev = self.a[li]
                    dw = np.dot(a_prev.T, dz)
                    db = np.sum(dz, axis=0, keepdims=True)
                    l["w"] -= self.lr * dw
                    l["b"] -= self.lr * db
                    if li > 0:
                        dz = np.dot(dz, l["w"].T) * self._drelu(self.z[li-1])
                losses.append(np.mean((out - yb)**2))
            if ep % 10 == 0:
                print(f"Epoch {ep}: loss {np.mean(losses):.4f}")

    def predict(self, X):
        return self.forward(X)

    def save(self, path="data/model_weights.npz"):
        np.savez(path, **{f"w{i}": l["w"] for i,l in enumerate(self.layers)},
                        **{f"b{i}": l["b"] for i,l in enumerate(self.layers)})

    def load(self, path="data/model_weights.npz"):
        data = np.load(path)
        for i,l in enumerate(self.layers):
            l["w"] = data[f"w{i}"]
            l["b"] = data[f"b{i}"]

def fetch_rss():
    all_articles = []
    for url in RSS_URLS:
        try:
            r = requests.get(url, timeout=15)
            r.raise_for_status()
            soup = BeautifulSoup(r.content, "xml")
            entries = soup.find_all("entry")
            for e in entries:
                title = e.find("title").text
                content = e.find("content").text
                all_articles.append({"title": title, "text": content})
            print(f"[ℹ️] RSS: found {len(entries)} articles from feed: {url}")
        except Exception as e:
            print(f"[!] RSS fetch failed for {url}: {e}")
    return all_articles

def collect_links_selenium():
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    driver = webdriver.Chrome(options=options)
    driver.get(START_URL)
    time.sleep(5)
    soup = BeautifulSoup(driver.page_source, "html.parser")
    driver.quit()
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("http") and "intellinews.com" in href:
            if ARTICLE_PATTERN.search(href):
                clean = href.split("?")[0]
                links.add(clean)
    print(f"[ℹ️] Selenium: collected {len(links)} candidate article links")
    return list(links)

def text_features(text: str):
    words = text.split(); n = len(words)
    avg_len = np.mean([len(w) for w in words]) if words else 0
    sents = re.split(r"[.!?]", text); sents = [s.strip() for s in sents if s.strip()]
    avg_sent = np.mean([len(s.split()) for s in sents]) if sents else 0
    numbers = sum(1 for w in words if w.isdigit())
    caps = sum(1 for w in words if w.isupper())
    return np.array([n, avg_len, avg_sent, numbers, caps], dtype=float)

def build_dataset(limit=100):
    articles = fetch_rss()
    articles = articles[:limit]
    print(f"[ℹ️] Total articles to process: {len(articles)}")

    X, y = [], []
    for idx, article in enumerate(articles, 1):
        try:
            body = article['text']
            if not body or not body.strip():
                print(f"[!] Skipped empty or invalid article: {article['title']}")
                continue
            feats = text_features(body)
            X.append(feats)
            y.append(1.0)
            print(f"[+] ({idx}) {article['title']} — {len(body.split())} words")
        except Exception as e:
            print(f"[!] Failed processing {article['title']}: {e}")

    if X:
        X, y = np.array(X), np.array(y)
        np.save(DATA_DIR / "X.npy", X)
        np.save(DATA_DIR / "y.npy", y)
        print(f"[✅] Built dataset: {X.shape[0]} samples, {X.shape[1]} features")
    else:
        print("[❌] No articles processed — dataset not created")

def train_model():
    X = np.load("data/X.npy")
    y = np.load("data/y.npy")
    agent = AdvancedNeuralAgent(input_size=X.shape[1])
    agent.train(X, y, epochs=200)
    agent.save("data/model_weights.npz")
    print("[✅] Model trained and saved.")

def rewrite_and_score_article(title: str, body: str, api_key: str) -> (str, float):
    """
    Rewrites an article in IntelliNews style and returns the rewritten text and a style score.
    """
    llm = ChatOpenAI(model_name="gpt-4o", temperature=0.5, api_key=api_key)
    
    messages = [
        SystemMessage(content=rules.get_writing_style_guide()),
        HumanMessage(content=body)
    ]
    
    resp = llm.invoke(messages)
    rewritten = resp.content.strip()

    # Style score with NN
    feats = text_features(rewritten).reshape(1, -1)
    agent = AdvancedNeuralAgent(input_size=feats.shape[1])
    try:
        agent.load("data/model_weights.npz")
        score = agent.predict(feats)[0, 0]
    except Exception:
        score = 0.0

    return rewritten, score