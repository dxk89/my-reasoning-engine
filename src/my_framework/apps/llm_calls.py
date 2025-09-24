# File: src/my_framework/apps/llm_calls.py

from my_framework.models.openai import ChatOpenAI
from my_framework.core.schemas import SystemMessage, HumanMessage
from my_framework.agents.utils import INDUSTRY_MAP, PUBLICATION_MAP, COUNTRY_MAP
from my_framework.parsers.standard import PydanticOutputParser
from .schemas import ArticleMetadata
import json
from typing import List
from . import rules  # Import the new rules file

def log(message):
    print(f"   - {message}", flush=True)

def get_initial_draft(llm: ChatOpenAI, user_prompt: str, source_content: str) -> str:
    # ... (This function remains the same)
    log("-> Building prompt for initial draft.")
    draft_prompt = [
        SystemMessage(content=rules.INITIAL_DRAFT_SYSTEM_PROMPT),
        HumanMessage(content=f"ADDITIONAL PROMPT INSTRUCTIONS: \"{user_prompt}\"\n\nSOURCE CONTENT:\n---\n{source_content}\n---\n\nWrite "
                             "the initial draft of the article now.")
    ]
    log("-> Sending request to LLM for initial draft...")
    draft_response = llm.invoke(draft_prompt)
    draft_article = draft_response.content
    log(f"-> Initial draft received ({len(draft_article)} characters).")
    return draft_article


def get_revised_article(llm: ChatOpenAI, source_content: str, draft_article: str, user_prompt: str, source_url: str) -> str:
    """
    Revises a draft article based on the source content and user prompt, with a strict focus on factual accuracy.
    """
    log("-> Building prompt for fact-checking and stylistic improvements.")
    revision_prompt = [
        SystemMessage(content=rules.REVISED_ARTICLE_SYSTEM_PROMPT),
        HumanMessage(content=f"USER PROMPT:\n---\n{user_prompt}\n---\n\nSOURCE CONTENT:\n---\n{source_content}\n---\n\nDRAFT ARTICLE:\n---\n{draft_article}\n---\n\nSOURCE URL: {source_url}\n\n"
                             "Please provide the revised, fact-checked, and stylistically improved article that adheres strictly to the source content and user prompt.")
    ]
    log("-> Sending request to LLM for revision...")
    revised_response = llm.invoke(revision_prompt)
    revised_article = revised_response.content
    log(f"-> Revised article received ({len(revised_article)} characters).")
    return revised_article

def get_country_selection(llm: ChatOpenAI, article_text: str) -> List[str]:
    """Makes a dedicated LLM call to get the country selection."""
    log("   -> Getting country selection...")
    country_names = list(COUNTRY_MAP.keys())
    countries_str = "\n".join([f"- {name}" for name in country_names])
    
    prompt = [
        SystemMessage(content=rules.COUNTRY_SELECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"""
        Based on the article text below, select the most relevant country or countries.

        AVAILABLE COUNTRIES:
        ---
        {countries_str}
        ---

        ARTICLE TEXT:
        ---
        {article_text}
        ---

        Your response must be ONLY a comma-separated list of the selected country names.
        """)
    ]
    response = llm.invoke(prompt)
    return [name.strip() for name in response.content.split(',')]

def get_publication_selection(llm: ChatOpenAI, article_text: str) -> List[str]:
    """Makes a dedicated LLM call to get the publication selection."""
    log("   -> Getting publication selection...")
    publication_names = list(PUBLICATION_MAP.keys())
    publications_str = "\n".join([f"- {name}" for name in publication_names])

    prompt = [
        SystemMessage(content=rules.PUBLICATION_SELECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"""
        Based on the article text below, select the most relevant publication(s).

        AVAILABLE PUBLICATIONS:
        ---
        {publications_str}
        ---

        ARTICLE TEXT:
        ---
        {article_text}
        ---

        Your response must be ONLY a comma-separated list of the selected publication names. For example: "Slovenia Today, CEE Energy News Watch"
        """)
    ]
    response = llm.invoke(prompt)
    return [name.strip() for name in response.content.split(',')]

def get_industry_selection(llm: ChatOpenAI, article_text: str) -> List[str]:
    """Makes a dedicated LLM call to get the industry selection."""
    log("   -> Getting industry selection...")
    industry_names = list(INDUSTRY_MAP.keys())
    industries_str = "\n".join([f"- {name}" for name in industry_names])

    prompt = [
        SystemMessage(content=rules.INDUSTRY_SELECTION_SYSTEM_PROMPT),
        HumanMessage(content=f"""
        Based on the article text below, select the most relevant industry or industries.

        AVAILABLE INDUSTRIES:
        ---
        {industries_str}
        ---

        ARTICLE TEXT:
        ---
        {article_text}
        ---

        Your response must be ONLY a comma-separated list of the selected industry names.
        """)
    ]
    response = llm.invoke(prompt)
    return [name.strip() for name in response.content.split(',')]

def get_seo_metadata(llm: ChatOpenAI, revised_article: str) -> str:
    """
    Generates comprehensive SEO and CMS metadata using a Pydantic parser for the main content
    and separate, dedicated calls for taxonomic fields (country, publication, industry).
    """
    log("-> Building structured prompt for main SEO metadata...")
    
    parser = PydanticOutputParser(pydantic_model=ArticleMetadata)
    
    # --- Step 1: Get the main metadata using the robust Pydantic parser ---
    main_metadata_prompt = [
        SystemMessage(content=rules.SEO_METADATA_SYSTEM_PROMPT),
        HumanMessage(content=f"""
        {parser.get_format_instructions()}
        
        Please exclude the 'publications', 'countries', and 'industries' fields from your JSON output.
        
        Here is the article to analyze:
        ---
        {revised_article}
        ---
        """)
    ]
    
    log("-> Sending request to LLM for main metadata...")
    try:
        response = llm.invoke(main_metadata_prompt)
        parsed_output = parser.parse(response.content)
        metadata = parsed_output.model_dump()
        log("-> Main metadata received and validated.")
    except Exception as e:
        log(f"-> 🔥 A critical error occurred during main metadata generation: {e}")
        return json.dumps({"error": f"Failed to generate main metadata: {e}"})

    # --- Step 2: Make separate, robust calls for taxonomic data ---
    try:
        metadata['countries'] = get_country_selection(llm, revised_article)
        metadata['publications'] = get_publication_selection(llm, revised_article)
        metadata['industries'] = get_industry_selection(llm, revised_article)
        log("-> All taxonomic data successfully retrieved.")
    except Exception as e:
        log(f"-> 🔥 A critical error occurred during taxonomic data retrieval: {e}")
        return json.dumps({"error": f"Failed to retrieve taxonomic data: {e}"})

    return json.dumps(metadata)