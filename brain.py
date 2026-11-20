import yaml
import json
import os
from pathlib import Path
from ollama import Client as OllamaClient
from google import genai
from google.genai.errors import APIError
from memory import Memory

# Directory where THIS script lives
_SCRIPT_DIR = Path(__file__).resolve().parent

class Brain:
    def __init__(self, config_path="config.yaml"):
        config_file = _SCRIPT_DIR / config_path
        with open(config_file, "r") as f:
            self.config = yaml.safe_load(f)
            
        brain_config = self.config.get("brain", {})
        self.provider = brain_config.get("provider", "gemini")
        self.model = brain_config.get("model", "gemini-3-flash-preview")
        self.ollama_model = brain_config.get("ollama_model", "llama3.1:8b")
        self.ollama_base_url = brain_config.get("ollama_base_url", "http://localhost:11434")
        self.system_prompt = brain_config.get("system_prompt", "You are Siya, an AI companion.")
        
        db_path = self.config.get("memory", {}).get("db_path", "data/siya_memory.db")
        self.memory = Memory(str(_SCRIPT_DIR / db_path))
        
        if self.provider == "ollama":
            self.ollama_client = OllamaClient(host=self.ollama_base_url)
            self.gemini_client = None
        elif self.provider == "gemini":
            api_key = brain_config.get("gemini_api_key") or os.environ.get("GEMINI_API_KEY")
            self.gemini_client = genai.Client(api_key=api_key)
            self.ollama_client = None
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

    def chat(self, user_input):
        self.memory.add_conversation_turn("user", user_input)
        
        ltm_context = self.memory.format_long_term_memory_for_prompt()
        full_system_prompt = self.system_prompt
        if ltm_context:
            full_system_prompt += f"\n\n{ltm_context}"

        history = self.memory.get_recent_conversation(limit=12)
        
        try:
            if self.provider == "gemini":
                assistant_reply = self._chat_gemini(full_system_prompt, history)
            elif self.provider == "ollama":
                assistant_reply = self._chat_ollama(full_system_prompt, history)
        except APIError as e:
            if e.code == 429:
                print("Gemini rate limit exceeded (429).")
                assistant_reply = "I'm sorry, I'm thinking a bit too fast right now. Please give me a moment."
            else:
                print(f"Gemini API Error: {e}")
                assistant_reply = "I'm having trouble connecting to my brain right now."
        except Exception as e:
            print(f"Error calling LLM: {e}")
            assistant_reply = "I'm having trouble thinking right now."
            
        self.memory.add_conversation_turn("assistant", assistant_reply)
        
        # Async/cheap extraction of new long term memories
        self._extract_and_store_memory(user_input, assistant_reply)
        
        return assistant_reply

    def _chat_gemini(self, system_prompt, history):
        contents = []
        for msg in history:
            role = "user" if msg["role"] == "user" else "model"
            contents.append(
                genai.types.Content(role=role, parts=[genai.types.Part.from_text(text=msg["content"])])
            )
            
        config = genai.types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=0.7,
        )
        
        response = self.gemini_client.models.generate_content(
            model=self.model,
            contents=contents,
            config=config
        )
        return response.text.strip()
        
    def _chat_ollama(self, system_prompt, history):
        messages = [{"role": "system", "content": system_prompt}]
        for msg in history:
            messages.append({"role": msg["role"], "content": msg["content"]})
            
        response = self.ollama_client.chat(model=self.ollama_model, messages=messages)
        return response['message']['content'].strip()
        
    def _extract_and_store_memory(self, user_input, assistant_reply):
        extraction_prompt = f"""
You are a memory extraction assistant. Analyze the following exchange between a user and an AI.
Determine if the user shared a durable fact worth remembering (e.g., preference, project, skill, goal, decision).
Do NOT store transient conversation details, greetings, or questions.

User: {user_input}
AI: {assistant_reply}

Return ONLY valid JSON with this schema, no markdown blocks, no other text:
{{"worth_storing": true/false, "category": "preferences|projects|skills|goals|decisions", "content": "Concise fact to remember"}}
"""
        try:
            result_text = ""
            if self.provider == "gemini":
                # We use JSON schema via Gemini
                schema = genai.types.Schema(
                    type=genai.types.Type.OBJECT,
                    properties={
                        "worth_storing": genai.types.Schema(type=genai.types.Type.BOOLEAN),
                        "category": genai.types.Schema(type=genai.types.Type.STRING),
                        "content": genai.types.Schema(type=genai.types.Type.STRING),
                    },
                    required=["worth_storing", "category", "content"]
                )
                config = genai.types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=schema,
                    temperature=0.1
                )
                response = self.gemini_client.models.generate_content(
                    model=self.model,
                    contents=extraction_prompt,
                    config=config
                )
                result_text = response.text.strip()
            else:
                response = self.ollama_client.chat(
                    model=self.ollama_model,
                    messages=[{"role": "user", "content": extraction_prompt}],
                    format="json"
                )
                result_text = response['message']['content'].strip()
            
            # Simple cleanup in case LLM wraps in markdown
            if result_text.startswith("```json"):
                result_text = result_text[7:]
            if result_text.endswith("```"):
                result_text = result_text[:-3]
                
            data = json.loads(result_text)
            
            if data.get("worth_storing") and data.get("category") and data.get("content"):
                self.memory.add_long_term_memory(data["category"], data["content"])
                print(f"[Memory stored] {data['category']}: {data['content']}")
        except APIError as e:
            if e.code == 429:
                print(f"[Memory extraction failed] Gemini rate limit exceeded (429).")
            else:
                print(f"[Memory extraction failed] Gemini API Error: {e}")
        except Exception as e:
            print(f"[Memory extraction failed] Silently ignoring. Error: {e}")

if __name__ == "__main__":
    print("Testing brain.py. Ensure GEMINI_API_KEY is set or Ollama is running.")
    try:
        brain = Brain()
        print(f"Brain initialized with provider: {brain.provider}")
        
        print("\nUser: Hi, I'm working on a python project called Siya.")
        reply = brain.chat("Hi, I'm working on a python project called Siya.")
        print(f"Siya: {reply}")
        
        print("\nUser: Just to remind you, I prefer short responses.")
        reply = brain.chat("Just to remind you, I prefer short responses.")
        print(f"Siya: {reply}")
        
        print("\nLet's check what got stored in LTM:")
        ltm = brain.memory.get_all_long_term_memories()
        for m in ltm:
            print(f"- {m['category']}: {m['content']}")
            
    except Exception as e:
        print(f"Test failed: {e}")
