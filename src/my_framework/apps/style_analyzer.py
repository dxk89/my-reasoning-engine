# File: my-journalist-project/my_framework/src/my_framework/apps/style_analyzer.py

import nltk
import numpy as np
import spacy
import re
from collections import Counter
from .style_guru import fetch_rss

# Download necessary NLTK and spaCy data
try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    print("Downloading spaCy model 'en_core_web_sm'...")
    from spacy.cli import download
    download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")

def analyze_articles(articles):
    """
    Analyzes a list of articles to create a style profile.
    """
    all_text = " ".join([article['text'] for article in articles])
    doc = nlp(all_text)
    
    # 1. Lexico-syntactic
    pos_tags = [token.pos_ for token in doc]
    pos_freq = Counter(pos_tags)
    
    # 2. Sentence & Paragraph Rhythm
    sentences = [sent.text for sent in doc.sents]
    sentence_lengths = [len(sent.split()) for sent in sentences]
    avg_sentence_length = np.mean(sentence_lengths)
    stdev_sentence_length = np.std(sentence_lengths)
    short_sentence_cadence = len([s for s in sentence_lengths if s <= 8]) / len(sentence_lengths) if sentence_lengths else 0
    
    # 3. Lexicon & Phraseology
    words = [token.text for token in doc]
    bigrams = nltk.bigrams(words)
    trigrams = nltk.trigrams(words)
    bigram_freq = Counter(bigrams)
    trigram_freq = Counter(trigrams)
    
    # 4. Evidence & Sourcing
    quotes = re.findall(r'["“](.*?)["”]', all_text)
    quote_density = len(quotes) / len(words) * 1000 if words else 0
    
    attribution_verbs = ['said', 'added', 'noted', 'argued', 'claimed', 'reported']
    attribution_verb_freq = Counter([w.lower() for w in words if w.lower() in attribution_verbs])
    
    # 5. Rhetorical Moves
    signposting_words = ['still', 'however', 'by contrast', 'meanwhile']
    signposting_freq = Counter([w.lower() for w in words if w.lower() in signposting_words])
    
    # 6. Punctuation & Micro-Style
    em_dash_freq = all_text.count('—') / len(words) * 1000 if words else 0
    semicolon_freq = all_text.count(';') / len(words) * 1000 if words else 0
    
    # 7. Compression Ratio
    named_entities = len(doc.ents)
    numbers = len([token for token in doc if token.pos_ == 'NUM'])
    compression_ratio = (named_entities + numbers) / len(words) * 100 if words else 0
    
    style_profile = {
        "avg_sentence_length": f"{avg_sentence_length:.2f}",
        "stdev_sentence_length": f"{stdev_sentence_length:.2f}",
        "short_sentence_cadence": f"{short_sentence_cadence:.2%}",
        "pos_distribution": {k: f"{(v / len(pos_tags)):.2%}" for k, v in pos_freq.most_common(5)},
        "top_bigrams": [f"{' '.join(gram)}: {count}" for gram, count in bigram_freq.most_common(10)],
        "top_trigrams": [f"{' '.join(gram)}: {count}" for gram, count in trigram_freq.most_common(10)],
        "quote_density": f"{quote_density:.2f}",
        "top_attribution_verbs": [f"{verb}: {count}" for verb, count in attribution_verb_freq.most_common(3)],
        "signposting_freq": {k: v / len(words) * 1000 for k, v in signposting_freq.items()},
        "em_dash_freq": f"{em_dash_freq:.2f}",
        "semicolon_freq": f"{semicolon_freq:.2f}",
        "compression_ratio": f"{compression_ratio:.2f}"
    }
    
    return style_profile

def generate_style_sheet():
    """
    Fetches articles from RSS feeds and generates a style sheet.
    """
    print("[ℹ️] Generating new style sheet...")
    articles = fetch_rss()
    
    if articles:
        style_profile = analyze_articles(articles)
        
        # Create a "House Style Sheet" from the profile
        house_style_sheet = "## House Style Sheet\n\n"
        for key, value in style_profile.items():
            house_style_sheet += f"- **{key.replace('_', ' ').title()}**: {value}\n"
            
        print("[✅] Style sheet generated successfully.")
        return house_style_sheet
    else:
        print("[❌] No articles found to generate style sheet.")
        return None