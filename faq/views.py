import os
import json
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.shortcuts import render,redirect
import requests
from agno.agent import Agent
from agno.models.google import Gemini
from agno.tools.duckduckgo import DuckDuckGoTools
from agno.tools.yfinance import YFinanceTools
from .models import *
import pandas as pd
from sentence_transformers import SentenceTransformer, util
from agno.storage.sqlite import SqliteStorage
from .models import *
from django.contrib.auth import authenticate, login,get_user_model,logout
from django.contrib import messages
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
from datetime import datetime, date
import markdown as md  # Add this import
from agno.tools import tool
import sqlite3  # or use SQLAlchemy

User  = get_user_model()

@tool
def run_sql_query(query: str) -> str:
    print('inside this function')
    print(query,'>>>>>>>>>>>>>>>')
    """Executes an SQL query on the database and returns the result as text."""
    conn = sqlite3.connect("yt.sqlite3")
    cursor = conn.cursor()
    try:
        cursor.execute(query)
        results = cursor.fetchall()
        return str(results)
    except Exception as e:
        return f"Error executing SQL: {str(e)}"
    finally:
        conn.close()

storage=SqliteStorage(table_name="chatbot_knowladge", db_file="tmp/data.db")

# Load FAQ data if exists
faq_df = None
faq_embeddings = None
embedding_model = None

try:
    faq_df = pd.read_csv("FAQ.csv")
    embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
    faq_questions = faq_df["question"].tolist()
    faq_embeddings = embedding_model.encode(faq_questions, convert_to_tensor=True)
except FileNotFoundError:
    print("FAQ.csv not found. Skipping FAQ functionality.")
except Exception as e:
    print(f"Error loading FAQ data: {e}")

def get_faq_answer(user_query, threshold=0.75):
    if faq_df is None or faq_embeddings is None or embedding_model is None:
        return None
    
    query_embedding = embedding_model.encode(user_query, convert_to_tensor=True)
    cosine_scores = util.pytorch_cos_sim(query_embedding, faq_embeddings)[0]
    
    best_score = float(cosine_scores.max())
    best_idx = int(cosine_scores.argmax())

    if best_score >= threshold:
        return faq_df.iloc[best_idx]["answer"]
    return None


def chatbot(user_query):
    print('inside agent')

    # Step 1: Try to get FAQ match
    faq_answer = get_faq_answer(user_query)
    if faq_answer:
        print("Answer from FAQ CSV >>>>>>>>>>>")
        return faq_answer

    # Step 2: Enhanced LLM agent focused on astrology
    agent = Agent(
    model=Gemini(id="gemini-2.0-flash", api_key='AIzaSyA4hAH5EdfAGjVNoiF_U2lxUzNGkyVhXdw'),
    session_id="1",
    storage=storage,
    instructions=[
        "You are Agno, an expert AI news agent.",
        "Always answer user queries clearly, accurately, and in detail, no matter how simple the question.",
        "If you do not know the answer, or if the query requires up-to-date information, use the web search tool to find the most relevant and current results.",
        "Every time you use information from a source, always provide the full, clickable source URL in your response.",
        "Whenever you use information from a source, cite it clearly with a clickable link or the full URL.",
        "Always include images when they are relevant (e.g., people, locations, historical events).",
        "For every image, provide both the direct image URL and the source article URL separately.",
        "If multiple images are relevant, include several, each with its own image and article URLs.",
        "Your response must always be detailed, well-structured, and organized using headers, lists, or tables when appropriate, similar to Perplexity AI responses.",
        "Never ask the user for clarification or additional information; always answer with the information provided and your own research.",
        "Always reference your sources, even if you are confident in the answer.",
        "Always cite sources with full URLs. When using web search, include clickable links at the end of the response.",
        "When the query is about a person, location, or event, always provide at least one relevant image, with both the image URL and the source article URL.",
        "Always format your answers in markdown for readability.",
        "You are an expert news agent who provides factual information with all available resources.",
        "Always use ul when giving response in list instead of ol"
    ],
    add_history_to_messages=True,
    num_history_runs=20,
    tools=[DuckDuckGoTools(), run_sql_query,YFinanceTools()],
    description="You are a news agent that helps users find the latest news.",
    debug_mode=True,
    markdown=True,
)


    # Run the agent with tool step outputs
    result = agent.run(
        user_query,
        show_full_reasoning=False,
        return_intermediate_steps=True
    )

    # Correct attribute access
    response_content = result.content

    print(response_content, ">>>>>>>>>>>>>>>>>>>")
    return response_content



@csrf_exempt
def chatbot_api(request):
    print('inside api')
    if request.method != 'POST':
        return JsonResponse({'status': False, 'error': 'Invalid request method'}, status=405)

    try:
        data = json.loads(request.body)
        user_query = data.get('query')
        
        


        if not user_query:
            return JsonResponse({'status': False, 'error': 'No query provided'}, status=400)

        result = chatbot(user_query)
        
        html_result = md.markdown(result)
        
        request.session['last_user_query'] = user_query
        request.session['last_bot_response'] = html_result
        
        # Uncomment if you want to store chat history
        # ChatHistory.objects.create(
        #     query=user_query,
        #     response=result
        # )

        return JsonResponse({'status': True, 'response': html_result, "response2":user_query})
    except Exception as e:
        print("Error:", e)
        return JsonResponse({'status': False, 'error': 'Internal server error'}, status=500)

@login_required
def home(request):
    return render(request, 'chatbot.html')

@csrf_exempt
def signup(request):
    if request.method == "POST":
        name = request.POST.get('name')
        print(name,'????????????')
        email = request.POST.get('email')
        password = request.POST.get('password')
        print(password,'passsssssssss')
        
        if User.objects.filter(email=email).exists():
            messages.info(request, "Username taken")
            return redirect('/sign/')
        
        user = User.objects.create_user(
            username=email,
            name = name,
            email = email,
            password=password
        )
        
        messages.info(request, "Account created successfully!")
        return redirect('login')
    
    return render(request,'signup.html')

@csrf_exempt
def login_view(request):
    if request.method == "POST":
        email = request.POST.get('email')
        print(email,'eeeeeeeeeeeee')
        password = request.POST.get('password')
        print(password,'pppppppppppppppppppppp')
        user = authenticate(username=email,password=password)
        print(user,'userrrrrrrrrr')
        
        if user:
            login(request,user)
            return redirect('home')
        else:
            messages.info(request,"Invalid email or password")
            return redirect ('login')
        
    return render(request,'login.html')


def new(request):
    return render(request,'new.html')

def response(request):
    user_query = request.session.get('last_user_query')
    bot_response = request.session.get('last_bot_response')

    return render(request, 'response.html', {
        'user_query': user_query,
        'bot_response': bot_response,
    })
