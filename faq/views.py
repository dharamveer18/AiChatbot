import os
import json
from django.http import JsonResponse,StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render
import requests
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from .models import *
import pandas as pd
from agno.storage.sqlite import SqliteStorage
from .models import *
from django.views.decorators.csrf import csrf_exempt
import markdown 
import sqlite3  # or use SQLAlchemy
import re
from agno.tools.serpapi import SerpApiTools



storage=SqliteStorage(table_name="chatbot_knowladge", db_file="tmp/data.db")

def chatbot(user_query):
    refined_prompt = [
    "You are Agno, an expert AI news agent.",
    "Always answer user queries clearly, accurately, and in detail, no matter how simple the question.",
    "If you do not know the answer, or if the query requires up-to-date information, use the web search tool to find the most relevant and current results.",
    "Every time you use information from a source, always provide the full, clickable source URL in your response.",
    "Whenever you use information from a source, cite it clearly with a clickable link or the full URL.",
    "Always include images when they are relevant (e.g., people, locations, historical events).",
    "For every image, provide BOTH:",
    "  - The direct image URL (must be a public, accessible image that does not require login or payment and is not a placeholder or broken link).",
    "  - The source article URL where the image appears.",
    "Always verify that the image URL is live and accessible (returns HTTP 200 and displays the image) before including it in your response.",
    "If the first image found is unavailable or returns an error (e.g., 404), skip it and find another image that is accessible.",
    "If no valid image can be found after several attempts, state clearly that no available image was found.",
    "If multiple images are relevant, include several, each with its own image and article URLs.",
    "Your response must always be detailed, well-structured, and organized using headers, lists, or tables when appropriate, similar to Perplexity AI responses.",
    "Never ask the user for clarification or additional information; always answer with the information provided and your own research.",
    "Always reference your sources, even if you are confident in the answer.",
    "Always cite sources with full URLs. When using web search, include clickable links at the end of the response.",
    "When the query is about a person, location, or event, always provide at least one relevant image, with both the image URL and the source article URL.",
    "Always return all output in markdown with proper formatting, including images using ![]() and links using []().",
    "When giving a list, always use ul instead of ol.",
    "Always give image URLs that are public and accessible for all users.",
    "Do not include images that are likely to be blocked, require authentication, or are placeholders.",
    "Before including any image, check that the URL is not broken and the image loads successfully.",
    "You have to always search user query to the web even if you you have response always search user query on web and extract relevent image and artical",
    "always give full response don't until the full response come",
    "Always return all the url and links in a tag not any other tag.",
    "always call serpapi tools to get images and articles",
    "For every relevant image, return the following format:"
    "**Image:** " 
    "![Alt text](IMAGE_URL)"  
    "[Source Article](SOURCE_URL)"
]


    agent = Agent(
        model=Gemini(id="gemini-2.0-flash", api_key='AIzaSyA4hAH5EdfAGjVNoiF_U2lxUzNGkyVhXdw'),
        # session_id="1",
        # storage=storage,
        instructions=refined_prompt,
        # add_history_to_messages=True,
        # num_history_runs=20,
        tools=[SerpApiTools(api_key='37e3812026b4e1ba471a6eb5d95a20251a09d24f1606928b9336bf3da304af79'),YFinanceTools()],
        description="You are a news agent that helps users find the latest news.",
        # debug_mode=True,
        # markdown=True,
    )



    # Run the agent with tool step outputs
    result = agent.run(
    # f"Search for news about '{user_query}' and return at least 3 public and accessible images with direct image URL and article URL using SerpApiTools.",
        user_query,
        show_full_reasoning=False,
        return_intermediate_steps=True,
        stream=True
    )
    print("Result:", result)
    # Correct attribute access
    for chunk in result:
        content = getattr(chunk, "content", "")
        if isinstance(content, str):
            yield content

@csrf_exempt
def chatbot_api(request):
    if request.method != 'POST':
        return JsonResponse({'status': False, 'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        user_query = data.get('query')

        if not user_query:
            return JsonResponse({'status': False, 'error': 'No query provided'}, status=400)

        result = chatbot(user_query)
        
        def formatted_stream():
            html_result = ""
            try:
                for chunk in result:
                    print("Chunk:", chunk)
                    yield chunk
            except Exception as e:
                yield f"<p>Error occurred: {str(e)}</p>"
            else:
                request.session['last_user_query'] = user_query
                request.session['last_bot_response'] = html_result


        return StreamingHttpResponse(formatted_stream(), content_type='text/html')  #type: ignore

        # html_result = result
        
        # request.session['last_user_query'] = user_query
        # request.session['last_bot_response'] = html_result
        
        # # Uncomment if you want to store chat history
        # # ChatHistory.objects.create(
        # #     query=user_query,
        # #     response=result
        # # )

        # return JsonResponse({'status': True, 'response': html_result, "response2":user_query})
    except Exception as e:
        print("Error:", e)
        return JsonResponse({'status': False, 'error': 'Internal server error'}, status=500)

def home(request):
    return render(request, 'chatbot.html')

def new(request):
    return render(request,'new.html')

def response(request):
    user_query = request.session.get('last_user_query')
    bot_response = request.session.get('last_bot_response')

    return render(request, 'response.html', {
        'user_query': user_query,
        'bot_response': bot_response,
    })

@csrf_exempt
def chatbotAPI(request):
    if request.method != 'POST':
        return JsonResponse({'status': False, 'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        user_query = data.get('query')

        if not user_query:
            return JsonResponse({'status': False, 'error': 'No query provided'}, status=400)

        result = chatbot(user_query)  # result yields markdown chunks

        html_result = ""
        for chunk in result:
            html_chunk = markdown.markdown(chunk)
            html_result += html_chunk

        # Save user query and bot response in session for next page
        request.session['last_user_query'] = user_query
        request.session['last_bot_response'] = html_result

        return JsonResponse({'status': True})
    except Exception as e:
        return JsonResponse({'status': False, 'error': str(e)}, status=500)






# user_query = data.get(user_query)
# result = chatbot(user_query)
# def formatted_stream():
#             html_result = ""
#             markdown_output = ""
#             for chunk in result:
#                 if isinstance(chunk, str):
#                     markdown_output += chunk
#                 elif isinstance(chunk, dict) and "content" in chunk:
#                     markdown_output += chunk["content"]
#             html_result = markdown.markdown(markdown_output)
#             yield html_result
#             print(user_query,'user query')
#             print(html_result,'html resulttt')
#             request.session['last_user_query'] = user_query
#             request.session['last_bot_response'] = html_result
            
            
            
# # my code        
            
# html_result = ""
#             for chunk in result:  # result yields markdown chunks
#                 # convert markdown chunk to html
#                 html_chunk = markdown.markdown(chunk)
#                 html_result += html_chunk
#                 print(html_result,'resulttttttttt')
#                 yield html_result
#             print(user_query,'user query')
#             print(html_result,'html resulttt')
#             request.session['last_user_query'] = user_query
#             request.session['last_bot_response'] = html_result
