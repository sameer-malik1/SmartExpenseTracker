import streamlit as st
import asyncio
from google import genai
from google.genai import types
from fastmcp import Client as FastMCPClient
from datetime import date,datetime
from dotenv import load_dotenv
from db_utils import register_user, login_user
import os
from utils.voice_models import speech_to_text, text_to_speech, speech_to_text2
from streamlit_mic_recorder import mic_recorder


load_dotenv()  # Load environment variables from .env file

gemini_api_key = os.getenv("gemini_api_key")

# Gemini client setup
gemini_client = genai.Client(api_key=gemini_api_key)

# session management
if "user" not in st.session_state:
    st.session_state.user = None
if "messages" not in st.session_state:
    st.session_state.messages = []

# ------------------ Authentication UI ------------------
def register_popup():
    st.subheader("🧾 Register New User")
    with st.form("register_form"):
        name = st.text_input("Full Name")
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        confirm = st.text_input("Confirm Password", type="password")
        submitted = st.form_submit_button("Register")
        if submitted:
            if password != confirm:
                st.error("Passwords do not match.")
            else:
                res = register_user(name, email, password)
                if res["ok"]:
                    st.success(res["message"])
                else:
                    st.error(res["message"])

def login_popup():
    st.subheader("🔑 Login")
    with st.form("login_form"):
        email = st.text_input("Email")
        password = st.text_input("Password", type="password")
        submitted = st.form_submit_button("Login")
        if submitted:
            res = login_user(email, password)
            if res["ok"]:
                st.session_state.user = res["user"]
                st.session_state.messages = []  # Clear messages on new login
                st.success(f"Welcome, {res['user']['name']} 👋")
                st.rerun()
            else:
                st.error(res["message"])

# ------------------ Chat Interface ------------------

# MCP HTTP client
mcp_client = FastMCPClient("http://127.0.0.1:8000/mcp")


def extract_text_from_response(response):
    """Extract text content from Gemini response, handling multiple parts."""
    try:
        # Try to get text from the response
        if hasattr(response, 'text') and response.text:
            return response.text
        
        # If that doesn't work, iterate through candidates and parts
        if hasattr(response, 'candidates') and response.candidates:
            text_parts = []
            for candidate in response.candidates:
                if hasattr(candidate, 'content') and hasattr(candidate.content, 'parts'):
                    for part in candidate.content.parts:
                        # Only get text parts, skip thought_signature and other non-text parts
                        if hasattr(part, 'text') and part.text:
                            text_parts.append(part.text)
            
            if text_parts:
                return "\n".join(text_parts)
        
        return "(No text response)"
    except Exception as e:
        print(f"Error extracting text: {e}")
        return "(Error extracting response)"


async def run_query(prompt: str):
    """Run a query through Gemini with MCP tools."""
    try:
        async with mcp_client:
            today_str = date.today().isoformat()
            user_id = st.session_state.user['id']
            
            response = await gemini_client.aio.models.generate_content(
                model="gemini-2.5-flash",  # Using the latest model
                contents=prompt,
                config=genai.types.GenerateContentConfig(
                    temperature=0,
                    tools=[mcp_client.session],
                    system_instruction=(
                        "You are a multi user expense tracker assistant. "
                        f"Today's date is {today_str}. "
                        f"The current user has user_id={user_id}. ALWAYS use this user_id when calling add_expense or list_expenses tools. "
                        "\n\nAvailable Operations:"
                        "\n1. ADD EXPENSE: Use add_expense(user_id, amount, category, note, date)"
                        "\n2. LIST EXPENSES: Use list_expenses(user_id, start_date, end_date)"
                        "\n   - Returns list of expenses with id, amount, category, note, date, if no date range is mentioned list all of the expenses"
                        "\n   - Use this to answer questions about specific categories"
                        "\n   - You can filter and calculate totals from the results"
                        "\n3. DELETE EXPENSE: Use delete_expense(user_id, expense_id) - Ask user to list expenses first to get the ID"
                        "\n4. EDIT EXPENSE: Use edit_expense(user_id, expense_id, amount, category, note, date) - Only update provided fields"
                        "\n5. ANALYZE EXPENSES: Use get_expense_analysis(user_id, start_date, end_date, group_by)"
                        "\n   - group_by: 'category' (default), 'date', or 'month'"
                        "\n   - Returns mean, median, total, min, max, std_dev, and grouped data"
                        "\n   - Use for general analytics, not category-specific queries"
                        "\n\nCATEGORY INFERENCE (VERY IMPORTANT):"
                        "\nYou MUST intelligently infer the category from the user's description. NEVER ask for category."
                        "\nUse these standard categories and map user descriptions to them:"
                        "\n- 'Food' → dinner, lunch, breakfast, snacks, meal, restaurant, cafe, coffee, pizza, burger, etc."
                        "\n- 'Groceries' → groceries, supermarket, vegetables, fruits, meat, dairy, shopping for food, etc."
                        "\n- 'Transport' → uber, taxi, bus, train, metro, fuel, gas, petrol, parking, ride, etc."
                        "\n- 'Travel' → flight, hotel, vacation, trip, tourism, airbnb, booking, etc."
                        "\n- 'Entertainment' → movie, concert, game, gaming, netflix, spotify, music, fun, party, etc."
                        "\n- 'Shopping' → clothes, shoes, electronics, gadgets, online shopping, amazon, etc."
                        "\n- 'Healthcare' → doctor, medicine, pharmacy, hospital, clinic, medical, health, etc."
                        "\n- 'Utilities' → electricity, water, gas bill, internet, phone bill, etc."
                        "\n- 'Rent' → rent, lease, apartment, housing, etc."
                        "\n- 'Education' → books, course, tuition, school, university, learning, etc."
                        "\n- 'Other' → anything that doesn't fit above categories"
                        "\nExamples:"
                        "\n- 'add 600 for dinner' → category='Food', note='dinner'"
                        "\n- 'spent 50 on uber' → category='Transport', note='uber'"
                        "\n- 'paid 100 for groceries' → category='Groceries'"
                        "\n- '200 for movie tickets' → category='Entertainment', note='movie tickets'"
                        "\n\nHANDLING CATEGORY-SPECIFIC QUERIES:"
                        "\nWhen user asks about spending on a specific category (e.g., 'how much on food', 'food expenses'):"
                        "\n1. Use list_expenses with the date range to get all expenses"
                        "\n2. Filter the results yourself to show only that category"
                        "\n3. Calculate the total for that category"
                        "\n4. Don't ask user for group_by or other details - just answer directly"
                        "\nExample: 'how much on food this month' → list_expenses(start='2025-10-01', end='2025-10-16'), filter for 'Food', sum amounts"
                        "\n\nGuidelines:"
                        "\n- ALWAYS infer category automatically - NEVER ask the user for it"
                        "\n- If no date is provided, use today's date (YYYY-MM-DD format)"
                        "\n- For date ranges like 'last week', 'this month', calculate the exact dates"
                        "\n- When deleting/editing, ask user to list expenses first if they don't provide an expense ID"
                        "\n- For analysis requests, intelligently choose the right approach:"
                        "\n  * Category-specific query → use list_expenses and filter"
                        "\n  * General analysis → use get_expense_analysis with group_by='category'"
                        "\n  * Time-based trends → use get_expense_analysis with group_by='month'"
                        "\n- Present analysis results in a clear, easy-to-understand format"
                        "\n- When showing expense lists, format them nicely with ID, amount, category, note, and date in table form compulsory"
                        "\n- Be conversational and helpful, explaining the results clearly"
                        "\n- Note: If no date is provided, use today's date with format YYYY-MM-DD. "
                        "\n- NEVER ask unnecessary clarifying questions - be proactive and intelligent"
                        "Provide clear, concise responses. After calling a tool, summarize the result for the user."
                        
                    ),
                ),
            )
            return response
    except Exception as e:
        print(f"Error in run_query: {e}")
        raise e


st.title("💰 AI Expense Tracker")

if not st.session_state.user:
    tab1, tab2 = st.tabs(["🔑 Login", "🧾 Register"])
    with tab1:
        login_popup()
    with tab2:
        register_popup()
else:
    # Sidebar with user info and quick actions
    with st.sidebar:
        st.write(f"👤 **{st.session_state.user['name']}**")
        st.write(f"📧 {st.session_state.user['email']}")
        st.divider()
        
        st.subheader("💡 Quick Commands")
        st.markdown("""
        **Add Expense** (categories auto-detected):
        - "Add 600 for dinner" → Food
        - "50 on uber" → Transport
        - "Add 200 for groceries yesterday"
        - "Spent 100 at the movies" → Entertainment
        
        **List Expenses:**
        - "Show all my expenses"
        - "List expenses for this month"
        - "Show expenses from last week"
        
        **Delete Expense:**
        - "Delete expense #5"
        - "Remove the last expense"
        
        **Edit Expense:**
        - "Edit expense #3, change amount to 75"
        - "Update expense #2, change category to food"
        
        **Analytics:**
        - "Show me expense analysis"
        - "What's my average spending?"
        - "Analyze my expenses by month"
        - "Show spending trends"
        """)
        
        st.divider()
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.user = None
            st.session_state.messages = []
            st.rerun()
    
    st.subheader("💬 Chat with Expense Tracker")

    # Display chat history
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Initialize session state variables
    if "audio_processed" not in st.session_state:
        st.session_state.audio_processed = False
    if "last_audio_name" not in st.session_state:
        st.session_state.last_audio_name = None
    
    user_input = st.chat_input("Ask me something (e.g. 'add 500 for travel'):")
    audio_value = st.audio_input("Record high quality audio", sample_rate=48000)
    print("audio value: ",audio_value)


    # Check if new audio is recorded
    if audio_value:
        # If new recording (different filename or new bytes)
        if audio_value.name != st.session_state.last_audio_name:
            st.session_state.audio_processed = False
            st.session_state.last_audio_name = audio_value.name

        # Only transcribe if not already processed
        if not st.session_state.audio_processed:
            os.makedirs("recordings", exist_ok=True)

            filename = datetime.now().strftime("%Y%m%d_%H%M%S") + "_" + audio_value.name
            filepath = os.path.join("recordings", filename)

            with open(filepath, "wb") as f:
                f.write(audio_value.read())

            with st.spinner("🪄 Transcribing..."):
                try:
                    user_input = speech_to_text(filepath)
                    st.session_state.audio_processed = True  # mark as handled
                except Exception as e:
                    st.error(f"Transcription failed: {e}")
                finally:
                    if os.path.exists(filepath):
                        os.remove(filepath)
    else:
        # No audio currently uploaded
        st.session_state.last_audio_name = None
        st.session_state.audio_processed = False

    # Now handle user input (text or transcribed)
    if user_input:
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        with st.chat_message("user"):
            st.markdown(user_input)

        with st.spinner("Processing..."):
            try:
                resp = asyncio.run(run_query(user_input))
                ai_response = extract_text_from_response(resp)

                st.session_state.messages.append({"role": "assistant", "content": ai_response})
                
                with st.chat_message("assistant"):
                    st.write(ai_response)
            except Exception as e:
                error_msg = f"Error: {str(e)}"
                st.session_state.messages.append({"role": "assistant", "content": error_msg})
                with st.chat_message("assistant"):
                    st.error(error_msg)
    