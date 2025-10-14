import streamlit as st
import asyncio
from google import genai
from google.genai import types
from fastmcp import Client as FastMCPClient
from datetime import date
from dotenv import load_dotenv
import os

load_dotenv()  # Load environment variables from .env file

gemini_api_key = os.getenv("gemini_api_key")



# ✅ Gemini client setup
gemini_client = genai.Client(api_key=gemini_api_key)

# ✅ MCP HTTP client
mcp_client = FastMCPClient("http://127.0.0.1:8000/mcp")

st.title("💰 AI Expense Tracker")

user_input = st.chat_input("Ask me something (e.g. 'add 500 for travel'):")

async def run_query(prompt: str):
    # Always connect inside an async context
    async with mcp_client:
        today_str = date.today().isoformat()
        # Use the new client API: gemini_client.models.generate_content()
        response = await gemini_client.aio.models.generate_content(
            model="gemini-2.5-flash",  # or gemini-flash-2.5 if available
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0,
                tools=[mcp_client.session],
                system_instruction=(
                    "You are an expense tracker assistant. "
                    f"Today's date is {today_str}. "
                    "When the user adds or lists expenses, use the MCP tools. "
                    "if no date is provided, use today's date with format YYYY-MM-DD."
                    "if user asks for listing the expenses and no date range is provided, list all expenses. "
                    "if user asks to list expenses without giving exact date instead he ask like 'from last monday to today' or 'for last week' or 'for last month' or 'for last year' or 'for this month' or 'for this year' or 'for today', convert dates accordingly e.g. if today is 2024-10-05 and user says 'from last monday to today' convert it to '2024-09-30' to '2024-10-05'. "
                    "Do not guess; always call the tool."
                ),
            ),
        )
        return response


if user_input:
    with st.chat_message("Human"):
        st.markdown(user_input)

    with st.spinner("Processing..."):
        with st.chat_message("AI"):
            # st.placeholder()  # Placeholder for the AI response
            try:
                resp = asyncio.run(run_query(user_input))
                # st.subheader("Response:")
                st.write(resp.text or "(No text response)")
            except Exception as e:
                st.error(f"Error: {e}")
