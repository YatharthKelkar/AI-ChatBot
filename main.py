import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
import dotenv
import os
import requests

# Optional: Colored text output
try:
    from colorama import init, Fore
    init(autoreset=True)
    use_color = True
except ImportError:
    use_color = False

# Load environment variables
dotenv.load_dotenv()

# Constants
MODEL_NAME = "microsoft/DialoGPT-medium"
SERPAPI_KEY = os.getenv("SERPAPI_KEY")  # Your key in .env

# Load tokenizer and model
def load_model_and_tokenizer(model_name):
    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForCausalLM.from_pretrained(model_name)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model.to(device)
    return tokenizer, model, device

# Formatted output
def print_bot(message):
    if use_color:
        print(Fore.CYAN + f"Chatbot: {message}")
    else:
        print(f"Chatbot: {message}")

# Enhanced Google Search via SerpAPI
def search_google(query):
    if not SERPAPI_KEY:
        return "Google search not available. API key missing."

    url = "https://serpapi.com/search"
    params = {
        "q": query,
        "api_key": SERPAPI_KEY,
        "engine": "google"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        result_parts = []

        # Answer box
        if "answer_box" in data:
            ab = data["answer_box"]
            if "answer" in ab:
                result_parts.append(f"Answer: {ab['answer']}")
            elif "snippet" in ab:
                result_parts.append(f"Snippet: {ab['snippet']}")
            elif "highlighted_words" in ab:
                result_parts.append("Highlights: " + ', '.join(ab["highlighted_words"]))

        # People also ask
        if "related_questions" in data:
            result_parts.append("\nPeople also ask:")
            for q in data["related_questions"][:3]:  # limit to top 3
                result_parts.append(f"- {q['question']}: {q.get('snippet', 'No answer found.')}")

        # Organic search results
        if "organic_results" in data and len(data["organic_results"]) > 0:
            first = data["organic_results"][0]
            snippet = first.get("snippet", "")
            link = first.get("link", "")
            result_parts.append(f"\nTop Result:\n{snippet}\nLink: {link}")

        return "\n".join(result_parts).strip() or "No useful result found."

    except Exception as e:
        return f"Search failed: {str(e)}"

# Chat loop
def chat_loop(tokenizer, model, device):
    print_bot("Hi! Ask anything! Type 'google: your question' to search Google. (Type 'exit' to quit)")
    chat_history_ids = None

    try:
        while True:
            user_input = input("You: ").strip()
            if user_input.lower() in ['exit', 'quit', 'bye']:
                print_bot("Goodbye! Take care :)")
                break

            if not user_input:
                print_bot("Please type something to continue.")
                continue

            if user_input.lower().startswith("google:"):
                query = user_input[7:].strip()
                result = search_google(query)
                print_bot(result)
                continue

            # Normal chatbot reply
            new_input_ids = tokenizer.encode(user_input + tokenizer.eos_token, return_tensors='pt').to(device)
            bot_input_ids = (
                torch.cat([chat_history_ids, new_input_ids], dim=-1)
                if chat_history_ids is not None else new_input_ids
            )

            chat_history_ids = model.generate(
                bot_input_ids,
                max_length=1000,
                pad_token_id=tokenizer.eos_token_id,
                do_sample=True,
                top_k=50,
                top_p=0.95,
                temperature=0.7
            )

            response = tokenizer.decode(chat_history_ids[:, bot_input_ids.shape[-1]:][0], skip_special_tokens=True)
            print_bot(response)

    except KeyboardInterrupt:
        print("\n")
        print_bot("Session ended manually.")

# Run it
def main():
    tokenizer, model, device = load_model_and_tokenizer(MODEL_NAME)
    chat_loop(tokenizer, model, device)

if __name__ == "__main__":
    main()
