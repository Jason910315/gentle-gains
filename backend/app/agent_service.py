import os
from openai import OpenAI
from app.schema import ChatMessage
from typing import List

class AgentService:
    def __init__(self):
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))