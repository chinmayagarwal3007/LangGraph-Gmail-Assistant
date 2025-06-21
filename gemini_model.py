from dotenv import load_dotenv
import os
from langchain_google_genai import ChatGoogleGenerativeAI
import streamlit as st

os.environ["GOOGLE_API_KEY"] = st.secrets["GEMINI_API_KEY"]
llm = ChatGoogleGenerativeAI(model="gemini-2.0-flash", temperature=0)


