import os
import sys
from dotenv import load_dotenv

# Ensure terminal can print Indic UTF-8 characters on Windows
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Load environment variables from .env
load_dotenv()

from sarvamai import SarvamAI

# Initialize Sarvam AI client by reading the API key from the environment
client = SarvamAI(api_subscription_key=os.environ.get("SARVAM_API_KEY"))

# Make a chat completion request to Sarvam's flagship Indic LLM
response = client.chat.completions(
    model="sarvam-105b",
    messages=[
        {"role": "user", "content": "नमस्ते! आप कैसे हैं? मुझे संक्षेप में बताइए कि आप कौन हैं।"}
    ],
)

# Print the model's response
print(response.choices[0].message.content)
