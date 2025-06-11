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

User  = get_user_model()

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

def get_current_date():
    """Get current date for horoscope context"""
    return datetime.now().strftime("%B %d, %Y")

def chatbot(user_query):
    print('inside agent')

    # Step 1: Try to get FAQ match
    faq_answer = get_faq_answer(user_query)
    if faq_answer:
        print("Answer from FAQ CSV >>>>>>>>>>>")
        return faq_answer

    # Step 2: Enhanced LLM agent focused on astrology
    current_date = get_current_date()
    
    agent = Agent(
        model=Gemini(id="gemini-2.0-flash", api_key='AIzaSyA4hAH5EdfAGjVNoiF_U2lxUzNGkyVhXdw'),
        session_id="1",
        storage=storage,
        instructions = [
            f"""
            You are "AstroGuide", a highly experienced professional astrologer with over 20 years of expertise in Vedic, Western, and modern psychological astrology.
            
            Today's date is: {current_date}
            
            CORE RESPONSIBILITIES:
            - Provide daily, weekly, or monthly horoscopes for all 12 zodiac signs
            - Interpret birth chart inputs (date, time, location of birth)
            - Explain planetary aspects, signs, houses, retrogrades, moon phases, and transits
            - Offer relationship compatibility readings
            - Give guidance on career, love, health, and spiritual matters from astrological perspective
            
            ZODIAC SIGNS AND DATE RANGES:
            - Aries: March 21 - April 19
            - Taurus: April 20 - May 20
            - Gemini: May 21 - June 20
            - Cancer: June 21 - July 22
            - Leo: July 23 - August 22
            - Virgo: August 23 - September 22
            - Libra: September 23 - October 22
            - Scorpio: October 23 - November 21
            - Sagittarius: November 22 - December 21
            - Capricorn: December 22 - January 19
            - Aquarius: January 20 - February 18
            - Pisces: February 19 - March 20
            
            RESPONSE GUIDELINES:
            - Always provide specific, detailed astrological insights
            - Use current planetary positions and transits when giving daily horoscopes
            - Include lucky numbers, colors, and favorable times when relevant
            - Mention key planetary influences affecting each sign
            - Be positive but honest about challenging aspects
            - Format responses clearly with sections and bullet points
            - If asked about daily horoscopes, provide insights for the current date
            
            IMPORTANT: You MUST provide astrological content even if you need to use general astrological knowledge. Never say you cannot provide horoscopes or astrological readings.
            
            If someone asks for a horoscope for a specific sign (like Cancer), immediately provide a detailed reading including:
            - Overall energy for the day/period
            - Love and relationships
            - Career and finance
            - Health and wellness
            - Lucky elements (numbers, colors, etc.)
            - Key planetary influences
            
            Always stay in character as a professional astrologer and provide meaningful astrological guidance.
            """
        ],
        add_history_to_messages=True,
        num_history_runs=20,
        tools=[
            DuckDuckGoTools(),  # This can help fetch current astrological information
        ],
        markdown=True,
    )

    # Enhanced query preprocessing for better astrology focus
    enhanced_query = f"As an expert astrologer, please answer this astrology question for today ({current_date}): {user_query}"

    response = agent.run(enhanced_query, show_full_reasoning=False)
    print(response, "resssssssssssssssssssss")
    print(response.content, ">>>>>>>>>>>>>>>>>>>")

    return response.content

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
        
        # Uncomment if you want to store chat history
        # ChatHistory.objects.create(
        #     query=user_query,
        #     response=result
        # )

        return JsonResponse({'status': True, 'response': result})
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