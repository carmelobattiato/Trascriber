# --- START OF FILE llm_processor.py ---

import os
import threading
import sys

# --- Optional Dependencies ---
# Wrap imports in try-except to handle missing libraries gracefully
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None # Flag as unavailable

try:
    import anthropic
except ImportError:
    anthropic = None # Flag as unavailable

try:
    import google.generativeai as genai
except ImportError:
    genai = None # Flag as unavailable

# DeepSeek doesn't have a dedicated official Python library like the others,
# It often uses an OpenAI-compatible API endpoint. We'll treat it like OpenAI
# but potentially use a different base_url and model name.

class LLMProcessor:
    """Handles interactions with various LLM APIs."""

    # Define common models for easier selection (can be expanded)
    MODEL_OPTIONS = {
        "OpenAI": ["gpt-4o", "gpt-4-turbo", "gpt-3.5-turbo"],
        "Anthropic": ["claude-3-5-sonnet-20240620", "claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"],
        "Gemini": ["gemini-1.5-pro-latest", "gemini-1.5-flash-latest", "gemini-1.0-pro"],
        "DeepSeek (OpenAI Compatible)": ["deepseek-chat", "deepseek-coder"] # Example names
    }

    def __init__(self, status_callback=None):
        self.status_callback = status_callback

    def _notify_status(self, message):
        if self.status_callback:
            try:
                # Ensure callback happens in the main thread if needed (GUI context)
                # This basic implementation assumes the caller handles thread safety if necessary
                self.status_callback(message)
            except Exception as e:
                print(f"LLM Processor: Error in status callback: {e}")

    def get_models_for_provider(self, provider_name):
        """Returns a list of models for the selected provider."""
        return self.MODEL_OPTIONS.get(provider_name, [])

    def process_text(self, provider, api_key, model, system_prompt, user_text):
        """
        Processes the user_text using the specified LLM provider, model, and prompt.

        Returns:
            tuple: (result_text, error_message)
                   result_text is the LLM response, or None on error.
                   error_message is a description of the error, or None on success.
        """
        self._notify_status(f"Processing with {provider} ({model})...")

        try:
            if provider == "OpenAI" or provider == "DeepSeek (OpenAI Compatible)":
                if not OpenAI:
                    return None, "OpenAI library not installed. Please run: pip install openai"
                client_params = {"api_key": api_key}
                # For DeepSeek or other compatible APIs, you might need a base_url
                if provider == "DeepSeek (OpenAI Compatible)":
                    # IMPORTANT: Replace with the actual DeepSeek API endpoint if different
                    client_params["base_url"] = "https://api.deepseek.com" # Example
                    # Or allow user to configure base_url in the GUI later

                client = OpenAI(**client_params)
                messages = []
                if system_prompt:
                    messages.append({"role": "system", "content": system_prompt})
                messages.append({"role": "user", "content": user_text})

                response = client.chat.completions.create(
                    model=model,
                    messages=messages
                )
                result = response.choices[0].message.content
                return result, None

            elif provider == "Anthropic":
                if not anthropic:
                    return None, "Anthropic library not installed. Please run: pip install anthropic"
                client = anthropic.Anthropic(api_key=api_key)
                messages = [{"role": "user", "content": user_text}]
                # Anthropic's recommended way is a system parameter + user message
                response = client.messages.create(
                    model=model,
                    system=system_prompt if system_prompt else None, # Pass system prompt here
                    messages=messages,
                    max_tokens=4096 # Set a reasonable max_tokens
                )
                result = response.content[0].text
                return result, None

            elif provider == "Gemini":
                if not genai:
                    return None, "Google GenerativeAI library not installed. Please run: pip install google-generativeai"
                genai.configure(api_key=api_key)
                # Gemini combines system instruction and first user message
                full_prompt = f"{system_prompt}\n\n{user_text}" if system_prompt else user_text
                generation_config = genai.types.GenerationConfig(
                    # candidate_count=1, # Default is 1
                    # stop_sequences=None,
                    # max_output_tokens=None, # Let the API decide default? Or set one?
                    # temperature=0.9, # Example temperature
                )
                safety_settings= [ # Adjust as needed
                    {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                    {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_MEDIUM_AND_ABOVE"},
                ]

                gemini_model = genai.GenerativeModel(
                    model_name=model,
                    generation_config=generation_config,
                    safety_settings=safety_settings,
                    system_instruction=system_prompt if system_prompt else None # Use system_instruction parameter
                )
                # Pass just the user text now, as system prompt is handled separately
                response = gemini_model.generate_content(user_text)

                # Handle potential blocks or errors in response
                if not response.candidates:
                     # Check if prompt was blocked
                     if response.prompt_feedback.block_reason:
                         return None, f"Processing blocked by Gemini safety filters: {response.prompt_feedback.block_reason}"
                     else:
                         return None, "Gemini returned no candidates without a specific block reason."
                # Check if the candidate itself finished due to safety or other reason
                first_candidate = response.candidates[0]
                if first_candidate.finish_reason.name != "STOP":
                    return None, f"Gemini generation stopped unexpectedly: {first_candidate.finish_reason.name}"
                # Check for empty content (might happen if blocked silently)
                if not first_candidate.content or not first_candidate.content.parts:
                    return None, "Gemini returned empty content, potentially due to safety filters."


                result = response.text # Access text directly
                return result, None

            else:
                return None, f"Unsupported LLM provider: {provider}"

        except ImportError as e:
             # This case is slightly redundant due to checks above, but good fallback
             return None, f"Missing library for {provider}: {e}. Please install the required package."
        except Exception as e:
            import traceback
            print(f"LLM Processor Error ({provider}):\n{traceback.format_exc()}")
            # Try to provide a more user-friendly error
            error_type = type(e).__name__
            error_details = str(e)
            # Common errors
            if "authentication" in error_details.lower() or "api key" in error_details.lower():
                 friendly_error = f"Authentication Error: Please check your API key for {provider}. ({error_type})"
            elif "rate limit" in error_details.lower():
                 friendly_error = f"Rate Limit Exceeded: You've made too many requests to {provider}. Please wait and try again. ({error_type})"
            elif "connection" in error_details.lower() or "network" in error_details.lower():
                 friendly_error = f"Connection Error: Could not connect to {provider}. Check your internet connection. ({error_type})"
            elif "not found" in error_details.lower() and ("model" in error_details.lower() or provider.lower() in error_details.lower()):
                 friendly_error = f"Model Not Found: The model '{model}' might not be available for {provider} or your API key plan. ({error_type})"
            else:
                 friendly_error = f"Error during processing with {provider}: {error_details} ({error_type})"

            return None, friendly_error

# --- END OF FILE llm_processor.py ---