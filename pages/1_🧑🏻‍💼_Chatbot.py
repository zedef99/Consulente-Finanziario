# Import necessary libraries
from openai import OpenAI
import streamlit as st
import time
import os
import json
import yfinance as yf   

def getStockPrice(ticker):
    # Fetch data for the given ticker symbol
    stock = yf.Ticker(ticker)

    # Get the latest closing price
    hist = stock.history(period="1d")
    latest_price = hist['Close'].iloc[-1]

    return latest_price


def handle_function(run):
    tools_to_call = run.required_action.submit_tool_outputs.tool_calls
    tools_output_array = []
    for each_tool in tools_to_call:
        tool_call_id = each_tool.id
        function_name = each_tool.function.name
        function_arg = each_tool.function.arguments
        print("Tool ID:" + tool_call_id)
        print("Function to Call:" + function_name )
        print("Parameters to use:" + function_arg)

        if (function_name == 'get_stock_price'):
            arguments_str = each_tool.function.arguments
            arguments_dict = json.loads(arguments_str)
            symbol = arguments_dict['symbol']
            st.sidebar.write('get stock price for ', symbol)

            output = str(getStockPrice(symbol))
            tools_output_array.append({"tool_call_id": tool_call_id, "output": output})

    client.beta.threads.runs.submit_tool_outputs(
        thread_id = st.session_state.thread_id,
        run_id = run.id,
        tool_outputs=tools_output_array
    )    

# Initialize session state variables for file IDs and chat control
if "file_id_list" not in st.session_state:
    st.session_state.file_id_list = []

if "start_chat" not in st.session_state:
    st.session_state.start_chat = False

if "thread_id" not in st.session_state:
    st.session_state.thread_id = None

# Set up the Streamlit page with a title and icon
st.set_page_config(page_title="Consulente finanziario", page_icon="🧑🏻‍💼", layout="wide")
st.header("🧑🏻‍💼 Consulente Finanziario")

# Set your OpenAI Assistant ID here
assistant_id = os.getenv('ASSISTANT_ID')
openai_api_key = os.getenv('OPENAI_KEY')

# Initialize the OpenAI client (ensure to set your API key in the sidebar within the app)
client = OpenAI(api_key=openai_api_key, default_headers={"OpenAI-Beta" :"assistants=v2"})


# Button to start the chat session
if st.sidebar.button("Start Chat"):
    st.session_state.start_chat = True
    # Create a thread once and store its ID in session state
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id
    st.write("thread id: ", thread.id)

# Define the function to process messages with citations
def process_message_with_citations(message):
    message_content = message.content[0].text.value
    return message_content

# Only show the chat interface if the chat has been started
if st.session_state.start_chat:
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display existing messages in the chat
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # Chat input for the user
    if prompt := st.chat_input("Come posso aiutarti?"):
        # Add user message to the state and display it
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Add the user's message to the existing thread
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt
        )

        # Create a run with additional instructions
        run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_id,
            instructions="Rispondi alle domande sulla base del file di cui disponi."
        )

        # Poll for the run to complete and retrieve the assistant's messages
        while run.status not in ["completed", "failed"]:
            st.sidebar.write(run.status)
            if run.status == "requires_action":
                handle_function(run)
            time.sleep(1)
            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )
        st.sidebar.write(run.status)

        # Retrieve messages added by the assistant
        messages = client.beta.threads.messages.list(
            thread_id=st.session_state.thread_id
        )

        # Process and display assistant messages
        assistant_messages_for_run = [
            message for message in messages 
            if message.run_id == run.id and message.role == "assistant"
        ]
        for message in assistant_messages_for_run:
            full_response = process_message_with_citations(message)
            st.session_state.messages.append({"role": "assistant", "content": full_response})
            with st.chat_message("assistant"):
                st.markdown(full_response, unsafe_allow_html=True)