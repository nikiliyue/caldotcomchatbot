# app.py

import streamlit as st
from dotenv import load_dotenv
import os
import logging

from langchain_openai import ChatOpenAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage

# --- Load Environment Variables ---
# Load from .env file if it exists
load_dotenv() 

# Ensure the logging level is set to INFO so that all info() messages
# from your tools will be displayed in the terminal.
# If you want to see even more detail (e.g., from LangChain),
# you can change this to logging.DEBUG.
logging.basicConfig(
    level=logging.INFO, # <-- MAKE SURE THIS IS NOT logging.WARNING or logging.ERROR
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
# =============================================================================


# Import our custom tools
from cal_tools import list_scheduled_events, book_event, cancel_event

# --- Page Configuration ---
st.set_page_config(page_title="Cal.com AI Assistant", page_icon="📅")

# --- Helper Functions ---
def get_agent_executor(user_email, time_zone):
    """Creates and returns the LangChain agent executor."""
    
    # Ensure API keys are loaded
    if not os.getenv("OPENAI_API_KEY") or not os.getenv("CAL_API_KEY"):
        st.error("API keys for OpenAI or Cal.com are not set. Please configure them in the sidebar.")
        st.stop()
        
    # 1. Define the tools the agent can use
    tools = [list_scheduled_events, book_event, cancel_event]

    # 2. Create the LLM instance
    # We use gpt-4o as it's excellent with function calling
    llm = ChatOpenAI(model="gpt-4o", temperature=0)

    # 3. Create the prompt template
    # We include user's email and timezone in the system prompt for context
    prompt = ChatPromptTemplate.from_messages([
        ("system", f"""
            You are a helpful assistant for managing calendar events using Cal.com.
            - You can list, book, and cancel events.
            - When booking, you must confirm the desired date and time.
            - Before booking, you must confirm the details with the user.
            - The user's email is '{user_email}'. You should use this email for all operations.
            - The user's timezone is '{time_zone}'. Use this for booking.
            - When listing events, provide the Booking ID as it is required for cancellations.
            - Be polite and conversational.
        """),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 4. Create the agent
    agent = create_tool_calling_agent(llm, tools, prompt)

    # 5. Create the agent executor
    agent_executor = AgentExecutor(
        agent=agent, 
        tools=tools, 
        verbose=True, # Set to True to see agent's thought process in console
        handle_parsing_errors=True # Gracefully handle errors
    )
    
    return agent_executor

# --- Streamlit UI ---

st.title("📅 Cal.com AI Assistant")
st.caption("Manage your Cal.com bookings through chat.")

# Sidebar for configuration
with st.sidebar:
    st.header("⚙️ Configuration")
    st.info("Please provide your details below. Your Cal.com API key is stored securely and not shared.")
    
    user_email = st.text_input("Your Email Address", help="The email associated with your Cal.com bookings.")
    time_zone = st.text_input("Your Timezone", value="America/New_York", help="e.g., 'America/New_York' or 'Europe/London'.")
    
    st.markdown("---")
    # Load keys from .env but allow override
    cal_api_key = st.text_input("Cal.com API Key", type="password", value=os.getenv("CAL_API_KEY", ""), help="Get from Cal.com Settings > Developer.")
    openai_api_key = st.text_input("OpenAI API Key", type="password", value=os.getenv("OPENAI_API_KEY", ""), help="Using the key provided in the challenge.")
    
    # Update environment variables from sidebar input
    if cal_api_key:
        os.environ["CAL_API_KEY"] = cal_api_key
    if openai_api_key:
        os.environ["OPENAI_API_KEY"] = openai_api_key


# Initialize chat history in session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Display prior chat messages
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("AI", avatar="🤖"):
            st.markdown(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("Human", avatar="👤"):
            st.markdown(message.content)

# Main chat interface
if prompt := st.chat_input("What would you like to do? (e.g., 'Book a meeting for tomorrow at 2pm')"):
    
    # Check if user email is provided
    if not user_email:
        st.warning("Please enter your email address in the sidebar to begin.")
    else:
        with st.chat_message("Human", avatar="👤"):
            st.markdown(prompt)
        
        # Add user message to history
        st.session_state.chat_history.append(HumanMessage(content=prompt))

        # Get the agent executor
        agent_executor = get_agent_executor(user_email, time_zone)

        # Invoke the agent with the user's prompt
        with st.chat_message("AI", avatar="🤖"):
            with st.spinner("Thinking..."):
                response = agent_executor.invoke({
                    "input": prompt,
                    "chat_history": st.session_state.chat_history
                })
        
        # Display AI response
        st.markdown(response["output"])
        
        # Add AI response to history
        st.session_state.chat_history.append(AIMessage(content=response["output"]))