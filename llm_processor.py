# --- START OF MODIFIED llm_processor.py ---

import os
import threading
import sys
import typing # For hints

try: from openai import OpenAI
except ImportError: OpenAI = None
try: import anthropic
except ImportError: anthropic = None
try: import google.generativeai as genai
except ImportError: genai = None

class LLMProcessor:
    """Handles interactions with various LLM APIs."""
    MODEL_OPTIONS = { # Updated models
        "OpenAI": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "Anthropic": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        "Gemini": ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest", "gemini-1.0-pro"], # Gemini Pro 1.0 exists
        "DeepSeek (OpenAI Compatible)": ["deepseek-chat", "deepseek-coder"]
    }

    def __init__(self, status_callback=None):
        self.status_callback = status_callback

    def _notify_status(self, message):
        if self.status_callback:
            try: self.status_callback(message)
            except Exception as e: print(f"LLM Processor Error: Status callback failed: {e}", file=sys.__stderr__)

    def get_models_for_provider(self, provider_name):
        return self.MODEL_OPTIONS.get(provider_name, [])

    def process_text(self, provider: str, api_key: str, model: str,
                     # system_prompt: typing.Optional[str], # REMOVED system_prompt from signature
                     user_text: str) -> tuple[typing.Optional[str], typing.Optional[str]]:
        """
        Processes the user_text using the specified LLM provider and model.
        Assumes instructions/system prompts are already prepended to user_text by the caller if needed.
        """
        self._notify_status(f"Processing with {provider} ({model})...")
        print(f"[LLM Processor] Received text for {provider} ({model}):\n--- START TEXT ---\n{user_text[:200]}...\n--- END TEXT ---") # Debug print

        try:
            # --- OpenAI / DeepSeek ---
            if provider == "OpenAI" or provider == "DeepSeek (OpenAI Compatible)":
                if not OpenAI: return None, "OpenAI library not installed. pip install openai"
                client_params = {"api_key": api_key}
                if provider == "DeepSeek (OpenAI Compatible)":
                    client_params["base_url"] = "https://api.deepseek.com" # Example
                client = OpenAI(**client_params)
                # **** CHANGED: Send only user message ****
                messages = [{"role": "user", "content": user_text}]
                response = client.chat.completions.create(model=model, messages=messages)
                result = response.choices[0].message.content
                return result, None

            # --- Anthropic ---
            elif provider == "Anthropic":
                if not anthropic: return None, "Anthropic library not installed. pip install anthropic"
                client = anthropic.Anthropic(api_key=api_key)
                # **** CHANGED: Send only user message, no system parameter ****
                messages = [{"role": "user", "content": user_text}]
                response = client.messages.create(model=model, messages=messages, max_tokens=4096)
                # Handle potential list of content blocks
                if response.content and isinstance(response.content, list):
                    result = "".join([block.text for block in response.content if hasattr(block, 'text')])
                else: # Fallback for older versions or unexpected responses
                    result = response.content[0].text if response.content else ""
                return result, None

            # --- Gemini ---
            elif provider == "Gemini":
                if not genai: return None, "Google GenerativeAI library not installed. pip install google-generativeai"
                genai.configure(api_key=api_key)
                # **** CHANGED: Generate content directly from user_text, remove system_instruction ****
                generation_config = genai.types.GenerationConfig() # Use defaults or configure as needed
                safety_settings= [ {"category": c, "threshold": "BLOCK_MEDIUM_AND_ABOVE"} for c in ["HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH", "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT"]]
                gemini_model = genai.GenerativeModel(model_name=model, generation_config=generation_config, safety_settings=safety_settings)
                response = gemini_model.generate_content(user_text) # Pass combined text

                # Handle potential blocks or errors (remains mostly the same)
                if not response.candidates:
                     block_reason = getattr(response.prompt_feedback, 'block_reason', None)
                     return None, f"Processing blocked by Gemini safety filters: {block_reason}" if block_reason else "Gemini returned no candidates."
                first_candidate = response.candidates[0]
                finish_reason = getattr(first_candidate, 'finish_reason', None)
                if finish_reason and finish_reason != 1: # 1 is 'STOP' in the enum
                    return None, f"Gemini generation stopped unexpectedly: {genai.types.FinishReason(finish_reason).name}"
                if not first_candidate.content or not first_candidate.content.parts: return None, "Gemini returned empty content."
                result = "".join(part.text for part in first_candidate.content.parts if hasattr(part, 'text')) # Safer way to join parts
                return result, None

            else:
                return None, f"Unsupported LLM provider: {provider}"

        except ImportError as e: return None, f"Missing library for {provider}: {e}."
        except Exception as e:
            import traceback; print(f"LLM Processor Error ({provider}):\n{traceback.format_exc()}", file=sys.__stderr__)
            error_type = type(e).__name__; error_details = str(e)
            if any(s in error_details.lower() for s in ["authentication", "api key", "permission"]): friendly_error = f"Authentication Error: Check API key for {provider}. ({error_type})"
            elif "rate limit" in error_details.lower(): friendly_error = f"Rate Limit Exceeded for {provider}. Wait and retry. ({error_type})"
            elif any(s in error_details.lower() for s in ["connection", "network"]): friendly_error = f"Connection Error to {provider}. Check internet. ({error_type})"
            elif "not found" in error_details.lower() and ("model" in error_details.lower() or provider.lower() in error_details.lower()): friendly_error = f"Model Not Found: '{model}' for {provider}. ({error_type})"
            else: friendly_error = f"Error with {provider}: {error_details} ({error_type})"
            return None, friendly_error

# --- END OF MODIFIED llm_processor.py ---