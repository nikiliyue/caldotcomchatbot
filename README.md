# Cal.com AI Chatbot

This project is an interactive chatbot that allows users to manage their Cal.com bookings using natural language. It leverages OpenAI's function calling capabilities, LangChain for agent orchestration, and Streamlit for the web interface.

## Features

- **Book Events**: Schedule new meetings by specifying date, time, and reason.
- **List Events**: View all your upcoming, scheduled events.
- **Cancel Events**: Cancel an existing event using its ID.
- **Interactive UI**: A simple and clean web interface built with Streamlit.

## Tech Stack

- **Language**: Python 3.10+
- **LLM Framework**: LangChain
- **AI Model**: OpenAI GPT-4o (or other function-calling models)
- **Web UI**: Streamlit
- **API Integration**: Cal.com REST API

## Setup and Installation

Follow these steps to get the chatbot running locally.

### 1. Prerequisites

- Python 3.10 or higher
- A Cal.com account
- An OpenAI account (or the API key provided in the challenge)

### 2. Clone the Repository

```bash
git clone <repository_url>
cd cal-com-chatbot
```

### 3. Create a Virtual Environment

It's highly recommended to use a virtual environment to manage dependencies.

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 4. Install Dependencies

Install all the required Python packages from `requirements.txt`.

```bash
pip3 install -r requirements.txt
```

### 5. Configure Environment Variables

You need to set up your API keys and Cal.com User ID.

1.  **Create a `.env` file** in the root of the project directory by copying the example:
    ```bash
    cp .env.example .env 
    ```
    *(Note: You might need to create a `.env.example` or just create `.env` from scratch)*

2.  **Edit the `.env` file** and add your credentials:

    ```ini
    # .env file

    # OpenAI API Key (provided in the challenge)
    OPENAI_API_KEY="sk-proj-..."

    # Your Cal.com API Key
    # Go to Cal.com > Settings > Developer > API Keys > New
    CAL_API_KEY="your_cal_dot_com_api_key_here"
    ```

    **Note**: The application also allows you to enter these keys directly in the Streamlit UI sidebar, which can be useful for quick tests or deployments.

## How to Run the Application

With the setup complete, you can start the Streamlit application.

```bash
streamlit run app.py
```

Your web browser should automatically open to the chatbot interface, typically at `http://localhost:8501`.

## How to Use the Chatbot

1.  Open the web application in your browser.
2.  On the sidebar, enter your **Email Address** and verify your **Timezone**. This information is used by the AI to perform actions on your behalf.
3.  Start chatting! Here are some example commands:
    - **To list events**: `"show me my scheduled events"` or `"what meetings do I have?"`
    - **To book an event**: `"help me book a meeting"` or `"book a meeting with John Doe for tomorrow at 3pm to discuss the project"`
    - **To cancel an event**: First, list the events to get the **Booking ID**. Then, you can say: `"please cancel my event with ID 12345"`

## Bonus Features Implemented

-   **Cancel Event**: The `cancel_event` tool is fully implemented. The agent is prompted to first find the booking ID by listing events, making the process robust.
-   **Interactive Web UI**: A user-friendly web interface is built using Streamlit, allowing for real-time interaction and easy configuration.
-   **Rescheduling (Conceptual)**: While not a dedicated tool, the agent can handle rescheduling requests by combining cancellation and booking. A user can say, "I want to reschedule my 3pm meeting to 4pm," and the agent can use the `cancel_event` and `book_event` tools in sequence.