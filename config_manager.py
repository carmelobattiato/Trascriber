# --- START OF MODIFIED config_manager.py ---

import os
import json
import base64
import sys
import tkinter.messagebox as messagebox

CONFIG_FILE = "config.json"
OBFUSCATION_KEY = b"AudioScriptSecretKeyForObfuscation_KeepItSimple_v1"

class ConfigManager:
    """Handles loading and saving application configuration."""

    def __init__(self):
        self.config_data = {} # Holds loaded config

    # ... (_obfuscate, _deobfuscate methods remain the same) ...
    def _obfuscate(self, data: str) -> str:
        if not data: return ""
        try: data_bytes = data.encode('utf-8'); key = OBFUSCATION_KEY; key_len = len(key); xor_bytes = bytes([data_bytes[i] ^ key[i % key_len] for i in range(len(data_bytes))]); return base64.b64encode(xor_bytes).decode('utf-8')
        except Exception as e: print(f"ConfigManager Error: Failed to obfuscate data - {e}", file=sys.__stderr__); return ""
    def _deobfuscate(self, obfuscated_data: str) -> str:
        if not obfuscated_data: return ""
        try: xor_bytes = base64.b64decode(obfuscated_data.encode('utf-8')); key = OBFUSCATION_KEY; key_len = len(key); data_bytes = bytes([xor_bytes[i] ^ key[i % key_len] for i in range(len(xor_bytes))]); return data_bytes.decode('utf-8')
        except (base64.binascii.Error, ValueError, UnicodeDecodeError, Exception) as e: print(f"ConfigManager Error: Failed to deobfuscate data - {e}", file=sys.__stderr__); return ""

    def load_config(self) -> dict:
        """Loads configuration from JSON file."""
        print(f"ConfigManager: Loading configuration from {CONFIG_FILE}...")
        defaults = {
            "ui_language": "English",
            "transcription_model": "large",
            "transcription_language": "italiano",
            "transcription_use_gpu": False,
            "llm_provider": None,
            "llm_model": None,
            "llm_api_key_obfuscated": "",
            "custom_llm_templates": {} # **** ADDED Default for custom templates ****
        }
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                self.config_data = {**defaults, **loaded_data}
                print("ConfigManager: Configuration loaded successfully.")
                obfuscated_key = self.config_data.get("llm_api_key_obfuscated", "")
                self.config_data["llm_api_key"] = self._deobfuscate(obfuscated_key)
                if obfuscated_key and not self.config_data["llm_api_key"]: print("ConfigManager Warning: Could not deobfuscate API key.", file=sys.__stderr__)
                # **** Ensure custom templates key exists ****
                if "custom_llm_templates" not in self.config_data:
                    self.config_data["custom_llm_templates"] = {}
                print(f"  - Loaded {len(self.config_data.get('custom_llm_templates', {}))} custom templates.")
            else:
                print(f"ConfigManager: {CONFIG_FILE} not found. Using default settings.")
                self.config_data = defaults
                self.config_data["llm_api_key"] = ""
        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            print(f"ConfigManager Error: Failed to load {CONFIG_FILE} - {e}", file=sys.__stderr__)
            messagebox.showwarning("Config Load Error", f"Could not load settings from {CONFIG_FILE}.\nUsing default values.\n\nError: {e}")
            self.config_data = defaults
            self.config_data["llm_api_key"] = ""
            self.config_data["custom_llm_templates"] = {}

        self.config_data.pop("llm_api_key_obfuscated", None)
        return self.config_data

    def save_config(self, current_settings: dict):
        """Saves the provided settings dictionary to the config file."""
        print(f"ConfigManager: Saving configuration to {CONFIG_FILE}...")
        save_data = current_settings.copy()
        try:
            api_key = save_data.get("llm_api_key", "")
            save_data["llm_api_key_obfuscated"] = self._obfuscate(api_key)
            save_data.pop("llm_api_key", None)
            # **** Ensure custom templates are included if they exist ****
            if "custom_llm_templates" not in save_data:
                 save_data["custom_llm_templates"] = {} # Should be passed from gui.py gather method

            print(f"  - Saving LLM: Provider={save_data.get('llm_provider')}, Model={save_data.get('llm_model')}, Key Saved={'Yes' if api_key else 'No'}")
            print(f"  - Saving Transcription: Model={save_data.get('transcription_model')}, Lang={save_data.get('transcription_language')}, GPU={save_data.get('transcription_use_gpu')}")
            print(f"  - Saving UI Language: {save_data.get('ui_language')}")
            print(f"  - Saving {len(save_data.get('custom_llm_templates', {}))} custom templates.")

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4, ensure_ascii=False)
            print("ConfigManager: Configuration saved successfully.")
        except Exception as e:
            print(f"ConfigManager Error: Failed to save configuration - {e}", file=sys.__stderr__)

# --- END OF MODIFIED config_manager.py ---