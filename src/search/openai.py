"""
OpenAI GPT-4o mini integration for search result processing
Replaces Claude for search query optimization and result analysis
"""

import asyncio
import aiohttp
import json
from typing import Optional
from ..config import config

class OpenAIAPI:
    """Async client for OpenAI API"""
    
    def __init__(self, api_key: str, model: str = "gpt-4o-mini"):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
        # Map model names to API model IDs
        model_map = {
            "gpt-4o-mini": "gpt-4o-mini",
            "gpt-4o": "gpt-4o", 
            "gpt-4-turbo": "gpt-4-turbo",
            "gpt-4": "gpt-4",
            "mini": "gpt-4o-mini",
            "4o": "gpt-4o",
            "turbo": "gpt-4-turbo"
        }
        self.model = model_map.get(model, "gpt-4o-mini")
        
    async def create_completion(self, messages: list, max_tokens: int = 1000, temperature: float = 0.2) -> str:
        """Create a completion using OpenAI API"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        timeout = aiohttp.ClientTimeout(total=15)  # Faster timeout for API calls
        async with aiohttp.ClientSession(timeout=timeout) as session:
            async with session.post(self.base_url, headers=headers, json=payload) as response:
                if response.status == 200:
                    result = await response.json()
                    return result["choices"][0]["message"]["content"]
                else:
                    error_text = await response.text()
                    # Log detailed error info
                    from ..utils.logging import get_logger
                    logger = get_logger(__name__)
                    logger.error(f"OpenAI API error {response.status}: {error_text}")
                    logger.debug(f"Model: {self.model}, Max tokens: {max_tokens}")
                    raise Exception(f"OpenAI API error {response.status}: {error_text}")

async def openai_optimize_search_query(user_query: str, filtered_context: str = "", model: str = "gpt-4o-mini") -> str:
    """
    Use OpenAI to optimize a search query for better Google Search results
    """
    if not config.has_openai_api():
        return user_query  # Fallback to original query
    
    try:
        # Create OpenAI client with specified model
        openai_client = OpenAIAPI(config.OPENAI_API_KEY, model)
        
        # Build system message for search query optimization
        system_message = """You are a search assistant. Your task is to take a user's question or request and rewrite it into a concise, highly effective search engine query that would return the most relevant and accurate results.

Rules:
- Focus on **keywords** and important concepts only.
- Remove filler words, pronouns, or vague modifiers.
- If the request is vague, **infer the likely intent**.
- Don't use quotes, punctuation, or special operators unless necessary.
- Output ONLY the search query. No explanations."""

        # Build user message in the specified format
        if filtered_context and filtered_context.strip():
            user_message = f"""User request: {user_query}

Context: {filtered_context.strip()}

Search query:"""
        else:
            user_message = f"""User request: {user_query}

Search query:"""
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Call OpenAI API with lower token limit for optimization
        response = await openai_client.create_completion(
            messages=messages,
            max_tokens=100,
            temperature=0.1
        )
        
        # Clean up the response
        optimized_query = response.strip().strip('"\'')
        
        return optimized_query
        
    except Exception as e:
        return user_query  # Fallback to original query

async def summarize_webpage_content(webpage_content: str, title: str, url: str, channel=None) -> str:
    """
    Summarize individual webpage content using GPT-4o mini
    """
    if not config.has_openai_api():
        return f"**{title}**: Content extraction successful but OpenAI API not configured for summarization."
    
    try:
        # Create OpenAI client with GPT-4o mini for summarization
        openai_client = OpenAIAPI(config.OPENAI_API_KEY, "gpt-4o-mini")
        
        # Build summarization prompt
        system_message = """You are a skilled summarizer. Given the following webpage content, create a clear and detailed summary that captures:

- The main topic and purpose of the content
- Key facts, data, or important details mentioned
- Names, dates, places, or specific references that are important
- Any conclusions, opinions, or recommendations stated
- Relevant context or background needed to understand the content

Write the summary in clear, concise bullet points or short paragraphs.  
Adapt your style to fit the tone of the original content (technical or casual).  
Do not include any information not explicitly stated in the text."""
        
        user_message = f"""Webpage content:
\"\"\"
{webpage_content}
\"\"\"

Summary:"""
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Call OpenAI API with optimized settings for speed
        summary = await openai_client.create_completion(
            messages=messages,
            max_tokens=300,  # More detailed summaries for better final synthesis
            temperature=0.0  # Deterministic for faster processing
        )
        
        result = f"**{title}** ({url}):\n{summary}"
        
        
        return result
        
    except Exception as e:
        return f"**{title}** ({url}): Summarization failed - {str(e)}"


async def _two_stage_analysis(user_query: str, search_results: str, filtered_context: str, channel=None) -> str:
    """
    Two-stage analysis: First summarize each webpage, then synthesize final answer
    """
    import asyncio
    import re
    
    # Parse search results to extract individual webpage content
    webpage_sections = []
    
    # Split by numbered results (1., 2., etc.)
    sections = re.split(r'\n(\d+)\.\s\*\*([^*]+)\*\*\n', search_results)
    
    for i in range(1, len(sections), 3):  # Skip the first empty section, then process groups of 3
        if i + 2 < len(sections):
            number = sections[i]
            title = sections[i + 1]
            content_block = sections[i + 2]
            
            # Extract snippet and full content
            snippet_match = re.search(r'Snippet: (.*?)(?=\n)', content_block)
            snippet = snippet_match.group(1).strip() if snippet_match else ""
            
            full_content_match = re.search(r'Full Content \(\d+ chars\): (.*?)(?=\n\s*Source:)', content_block, re.DOTALL)
            full_content = full_content_match.group(1).strip() if full_content_match else ""
            
            # Combine snippet and full content
            combined_content = f"Google Snippet: {snippet}\n\nFull Page Content: {full_content}" if snippet else full_content
            
            if combined_content:
                # Extract URL from Source line
                source_match = re.search(r'Source: (.+)', content_block)
                url = source_match.group(1).strip() if source_match else "Unknown URL"
                
                webpage_sections.append({
                    'title': title,
                    'content': combined_content,
                    'url': url
                })
    
    if not webpage_sections:
        # Fallback if parsing failed
        return "Error: Could not parse webpage content for summarization."
    
    
    
    # Stage 1: Parallel summarization of individual webpages
    import time
    summary_start = time.time()
    summarization_tasks = [
        summarize_webpage_content(section['content'], section['title'], section['url'], channel)
        for section in webpage_sections
    ]
    
    # Execute all summarizations in parallel
    webpage_summaries = await asyncio.gather(*summarization_tasks, return_exceptions=True)
    summary_time = time.time() - summary_start
    
    
    # Filter out exceptions and combine summaries
    valid_summaries = []
    for summary in webpage_summaries:
        if isinstance(summary, Exception):
            continue
        valid_summaries.append(summary)
    
    if not valid_summaries:
        return "Error: All webpage summarizations failed."
    
    combined_summaries = "\n\n".join(valid_summaries)
    
    
    # Stage 2: Synthesize final answer using cleaner prompt structure
    synthesis_start = time.time()
    openai_client = OpenAIAPI(config.OPENAI_API_KEY, "gpt-4o-mini")
    
    system_message = """You are a helpful assistant. Below are summaries of multiple webpages related to a user's question.

Please provide a clear, concise, and accurate answer to the user's question using the summaries.

- Focus only on the most important information relevant to the question
- Be accurate - only include information explicitly stated in the summaries
- Be concise - aim for 300-400 words maximum
- Use Discord markdown formatting (**bold**, bullet points)
- Keep paragraphs short (2-3 sentences max)
- Avoid repetition between sources
- Integrate context naturally"""
    
    context_section = f"\n\nPrevious Context:\n{filtered_context.strip()}" if filtered_context and filtered_context.strip() else ""
    
    user_message = f"""User Question:
\"\"\"
{user_query}
\"\"\"
{context_section}

Webpage Summaries:
\"\"\"
{combined_summaries}
\"\"\"

Answer:"""
    
    messages = [
        {"role": "system", "content": system_message},
        {"role": "user", "content": user_message}
    ]
    
    # Set output limits for final responses
    max_tokens = 512
    
    # Call OpenAI API for final synthesis
    response = await openai_client.create_completion(
        messages=messages,
        max_tokens=max_tokens,
        temperature=0.2
    )
    synthesis_time = time.time() - synthesis_start
    
    
    # Calculate actual input tokens for the final synthesis prompt (combined_summaries is already in user_message)
    final_prompt_tokens = (len(system_message) + len(user_message)) // 4
    
    return f"**OpenAI GPT-4o Mini Web Search** ({len(webpage_sections)} sites, ~{final_prompt_tokens} tokens): {response}"


async def openai_search_analysis(user_query: str, search_results: str, filtered_context: str = "", model: str = "gpt-4o-mini", channel=None) -> str:
    """
    Use OpenAI to analyze search results and provide a comprehensive answer
    - GPT-4o mini: Uses two-stage approach (summarize pages, then synthesize)
    - GPT-4o: Uses single-stage approach (processes full content directly)
    """
    if not config.has_openai_api():
        return "OpenAI API not configured - cannot process search results"
    
    try:
        
        # Check if we have full webpage content and decide approach based on model
        if "Full Content (" in search_results:
            if model == "gpt-4o-mini":
                # Use two-stage approach for cost optimization
                return await _two_stage_analysis(user_query, search_results, filtered_context, channel)
            else:
                # GPT-4o can handle full content directly - use single-stage approach
                pass  # Fall through to single-stage processing
        
        # Single-stage approach for GPT-4o or snippet-only results
        
        # Create OpenAI client with specified model
        import time
        single_stage_start = time.time()
        openai_client = OpenAIAPI(config.OPENAI_API_KEY, model)
        
        # Build system message for search result analysis
        system_message = """You are an expert assistant. Using all the information provided below—including the user's query, previous context, and a large set of website content—generate a clear, concise, and comprehensive answer.

Instructions:
- Consider all the provided text carefully.
- Focus only on information relevant to the user's query.
- Integrate prior context to maintain continuity.
- Avoid repeating information.
- If conflicting information exists, note it briefly.
- Write the answer clearly and in a well-organized manner.
- Format the answer using Discord markdown:
  - Use **bold** for key points.
  - Use bullet points or numbered lists to organize information.
  - Use inline code blocks (`code`) for technical terms or code snippets.
  - Keep paragraphs short for readability.
- Keep the answer focused and as concise as possible given the input size.
- Optionally, limit your answer length to 1000 tokens."""

        # Build user message in the specified format
        context_section = filtered_context.strip() if filtered_context and filtered_context.strip() else "No previous context available."
        
        user_message = f"""User Query:
{user_query}

Previous Context:
{context_section}

Website Content:
{search_results}

Discord-formatted Answer:"""
        
        messages = [
            {"role": "system", "content": system_message},
            {"role": "user", "content": user_message}
        ]
        
        # Set reasonable output token limits based on model
        max_tokens = 2048 if model == "gpt-4o" else 512
        
        # Call OpenAI API
        response = await openai_client.create_completion(
            messages=messages,
            max_tokens=max_tokens,
            temperature=0.2
        )
        single_stage_time = time.time() - single_stage_start
        
        
        # Calculate actual input tokens for the single-stage approach
        single_stage_tokens = (len(system_message) + len(user_message)) // 4
        
        # Count websites in search results (look for numbered results like "1. **Title**")
        import re
        website_matches = re.findall(r'^\d+\.\s\*\*', search_results, re.MULTILINE)
        website_count = len(website_matches)
        
        # Get model display name
        model_names = {
            "gpt-4o-mini": "OpenAI GPT-4o Mini",
            "gpt-4o": "OpenAI GPT-4o", 
            "gpt-4-turbo": "OpenAI GPT-4 Turbo",
            "gpt-4": "OpenAI GPT-4"
        }
        model_display = model_names.get(model, f"OpenAI {model}")
        
        return f"**{model_display} Web Search** ({website_count} sites, ~{single_stage_tokens} tokens): {response}"
        
    except Exception as e:
        # Log the full error for debugging
        from ..utils.logging import get_logger
        logger = get_logger(__name__)
        logger.error(f"OpenAI search analysis failed: {e}")
        logger.debug(f"Query: {user_query[:100]}...")
        logger.debug(f"Model: {model}")
        logger.debug(f"Search results length: {len(search_results)}")
        
        return f"Error analyzing search results with OpenAI: {str(e)}"

async def test_openai_api() -> bool:
    """Test if OpenAI API is working properly"""
    if not config.has_openai_api():
        return False
    
    try:
        openai_client = OpenAIAPI(config.OPENAI_API_KEY)
        messages = [
            {"role": "system", "content": "You are a helpful assistant. Respond with exactly 'API test successful'."},
            {"role": "user", "content": "Test the API"}
        ]
        response = await openai_client.create_completion(
            messages=messages,
            max_tokens=50
        )
        return "API test successful" in response
    except Exception as e:
        return False