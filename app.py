import os
import json
import streamlit as st
import openai
from dotenv import load_dotenv
from scraper import fetch_data

# load keys
load_dotenv()

# Try environment variables first, then Streamlit secrets
openai.api_key = os.getenv("OPENAI_API_KEY")
if not openai.api_key:
    try:
        openai.api_key = st.secrets["OPENAI_API_KEY"]
    except:
        st.error("Please set OPENAI_API_KEY in environment or Streamlit secrets")
        st.stop()

st.title("NFA ChatBot")
query = st.text_input("Enter your query about a fund:")

def get_function_schema():
    return [
        {
            "name": "get_fund_data",
            "description": "Get data about a fund from Morningstar. Can fetch MER (cost), performance, or fund profile.",
            "parameters": {
                "type": "object",
                "properties": {
                    "fund": {
                        "type": "string",
                        "description": "The name of the fund to look up"
                    },
                    "data_points": {
                        "type": "array",
                        "items": {
                            "type": "string",
                            "enum": ["mer", "performance", "fund_profile"]
                        },
                        "description": "The data points to fetch. mer = management expense ratio/costs, performance = 1yr return, fund_profile = investment strategy and approach"
                    }
                },
                "required": ["fund", "data_points"]
            }
        }
    ]

def execute_function_call(function_name, arguments):
    """Execute the function call and return results"""
    if function_name == "get_fund_data":
        fund = arguments.get("fund")
        data_points = arguments.get("data_points", [])
        
        with st.spinner(f"Looking up {fund} data..."):
            try:
                # Import the new function
                from scraper import fetch_multiple_data
                # Fetch all data points in a single session
                results = fetch_multiple_data(fund, data_points)
            except ImportError:
                # Fallback to old method if new function not available
                results = {}
                for data_point in data_points:
                    try:
                        results[data_point] = fetch_data(fund, data_point)
                    except Exception as e:
                        results[data_point] = f"Error: {str(e)}"
        
        return results
    return None

def get_conversational_response(user_query, fund_data, fund_name):
    """Generate a professional response that advisors can use in client communications"""
    
    # Format the data for the prompt
    data_text = ""
    if "mer" in fund_data:
        data_text += f"Management Expense Ratio (MER): {fund_data['mer']}\n"
    if "performance" in fund_data:
        data_text += f"1-Year Performance: {fund_data['performance']}\n"
    if "fund_profile" in fund_data:
        data_text += f"Fund Profile: {fund_data['fund_profile']}\n"
    
    # Create a professional prompt
    prompt = f"""Based on the following Morningstar data about {fund_name}, provide a professional response that a financial advisor can use when writing to their client.

Query: {user_query}

Fund Data:
{data_text}

Instructions:
- Write professional, factual content without salutations or signatures
- Be concise and to the point
- Present data objectively without speculation
- If the query is about buy/sell recommendations, only reference the fund's investment strategy and profile
- For cost inquiries, state the MER with brief factual context
- For performance inquiries, present returns objectively
- Do not include "Dear Client" or sign-offs - the advisor will add these
- Do not provide investment advice or recommendations
- Write in a neutral, professional tone that can be incorporated into a larger email/letter"""

    response = openai.ChatCompletion.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "You are generating professional financial content for advisors to use in client communications. Provide factual, concise information without greetings or signatures."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.3
    )
    
    return response.choices[0].message.content

if query:
    try:
        # First, use OpenAI to understand intent and determine what data to fetch
        intent_response = openai.ChatCompletion.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are an assistant that determines what fund data is needed for advisor queries. Always identify the fund name. For buy/sell questions, always fetch the fund_profile."},
                {"role": "user", "content": query}
            ],
            functions=get_function_schema(),
            function_call="auto"
        )
        
        message = intent_response.choices[0].message
        
        if message.get("function_call"):
            # Parse the function call
            function_name = message["function_call"]["name"]
            arguments = json.loads(message["function_call"]["arguments"])
            
            # Execute the function to get data
            fund_data = execute_function_call(function_name, arguments)
            
            if fund_data:
                # Generate conversational response
                response = get_conversational_response(query, fund_data, arguments.get("fund"))
                st.write(response)
            else:
                st.write("Unable to retrieve the requested fund data. Please verify the fund name and try again.")
        else:
            # No function call needed - provide direct response
            st.write(message["content"])
            
    except Exception as e:
        st.error(f"Error: {str(e)}")
        st.info("Please verify the fund name and try again.")