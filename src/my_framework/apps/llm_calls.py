# File: src/my_framework/apps/llm_calls.py

from my_framework.models.openai import ChatOpenAI
from my_framework.core.schemas import SystemMessage, HumanMessage
from my_framework.agents.utils import INDUSTRY_MAP, PUBLICATION_MAP, COUNTRY_MAP
from my_framework.parsers.standard import PydanticOutputParser
from .schemas import ArticleMetadata
import json
from typing import List

def log(message):
    print(f"   - {message}", flush=True)

def get_initial_draft(llm: ChatOpenAI, user_prompt: str, source_content: str) -> str:
    # ... (This function remains the same)
    log("-> Building prompt for initial draft.")
    draft_prompt = [
        SystemMessage(content="You are an expert journalist. Your task is to write a professional, insightful, and "
                              "objective article based on the user's prompt and the provided source content. Focus on "
                              "financial, business, and political analysis of emerging markets."),
        HumanMessage(content=f"USER PROMPT: \"{user_prompt}\"\n\nSOURCE CONTENT:\n---\n{source_content}\n---\n\nWrite "
                             "the initial draft of the article now.")
    ]
    log("-> Sending request to LLM for initial draft...")
    draft_response = llm.invoke(draft_prompt)
    draft_article = draft_response.content
    log(f"-> Initial draft received ({len(draft_article)} characters).")
    return draft_article


def get_revised_article(llm: ChatOpenAI, source_content: str, draft_article: str) -> str:
    # ... (This function remains the same)
    log("-> Building prompt for fact-checking and stylistic improvements.")
    revision_prompt = [
        SystemMessage(content="You are a meticulous editor for intellinews.com. Your task is to review a draft article. "
                              "First, ensure every claim is fully supported by the provided SOURCE CONTENT, correcting "
                              "any inaccuracies. Second, refine the writing to match the professional, insightful, and "
                              "objective style of intellinews.com."),
        HumanMessage(content=f"SOURCE CONTENT:\n---\n{source_content}\n---\n\nDRAFT ARTICLE:\n---\n{draft_article}\n---\n\n"
                             "Please provide the revised, fact-checked, and stylistically improved article.")
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
        SystemMessage(content="You are an expert data extractor. Your only task is to identify the main country or countries discussed in the provided article text. "
                              "You must choose from the list of available countries. Your response must be a single, comma-separated string of the selected country names."),
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
        SystemMessage(content="You are an expert sub-editor. Your only task is to select the most appropriate publications for an article from a provided list. "
                              "You must choose the MOST SPECIFIC publication possible. Your response must be a single, comma-separated string of the selected publication names."),
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
        SystemMessage(content="You are an expert data analyst. Your only task is to select the most relevant industries for an article from a provided list. "
                              "You must choose the MOST SPECIFIC industry possible. Your response must be a single, comma-separated string of the selected industry names."),
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
        SystemMessage(content="You are an expert sub-editor. Your task is to generate a valid JSON object with the creative and SEO-related metadata for an article, following the provided schema. "
                              "Do NOT include 'publications', 'countries', or 'industries' in this JSON object."),
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