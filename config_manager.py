# --- START OF FILE config_manager.py ---

import os
import json
import base64
import sys
import tkinter.messagebox as messagebox # For showing errors during load

CONFIG_FILE = "config.json"
# Chiave semplice - NON SICURA! Solo per offuscamento leggero.
# Cambiare questa chiave invaliderà le API key salvate precedentemente.
OBFUSCATION_KEY = b"AudioScriptSecretKeyForObfuscation_KeepItSimple_v1"

class ConfigManager:
    """Handles loading and saving application configuration."""

    def __init__(self):
        self.config_data = {} # Holds loaded config

    # --- Simple Obfuscation/Deobfuscation (NOT SECURE!) ---
    def _obfuscate(self, data: str) -> str:
        """Obfuscates data using XOR and Base64."""
        if not data: return ""
        try:
            data_bytes = data.encode('utf-8')
            key = OBFUSCATION_KEY
            key_len = len(key)
            xor_bytes = bytes([data_bytes[i] ^ key[i % key_len] for i in range(len(data_bytes))])
            return base64.b64encode(xor_bytes).decode('utf-8')
        except Exception as e:
            print(f"ConfigManager Error: Failed to obfuscate data - {e}", file=sys.__stderr__)
            return ""

    def _deobfuscate(self, obfuscated_data: str) -> str:
        """Deobfuscates data using Base64 and XOR."""
        if not obfuscated_data: return ""
        try:
            xor_bytes = base64.b64decode(obfuscated_data.encode('utf-8'))
            key = OBFUSCATION_KEY
            key_len = len(key)
            data_bytes = bytes([xor_bytes[i] ^ key[i % key_len] for i in range(len(xor_bytes))])
            return data_bytes.decode('utf-8')
        except (base64.binascii.Error, ValueError, UnicodeDecodeError, Exception) as e:
            print(f"ConfigManager Error: Failed to deobfuscate data - {e}", file=sys.__stderr__)
            return "" # Return empty on error

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
            "llm_api_key_obfuscated": ""
        }
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded_data = json.load(f)
                # Merge loaded data with defaults (defaults take precedence if key missing in file)
                self.config_data = {**defaults, **loaded_data} # Loaded data overrides defaults
                print("ConfigManager: Configuration loaded successfully.")

                # Deobfuscate API key specifically
                obfuscated_key = self.config_data.get("llm_api_key_obfuscated", "")
                self.config_data["llm_api_key"] = self._deobfuscate(obfuscated_key) # Store deobfuscated version
                if obfuscated_key and not self.config_data["llm_api_key"]:
                     print("ConfigManager Warning: Could not deobfuscate API key.", file=sys.__stderr__)

            else:
                print(f"ConfigManager: {CONFIG_FILE} not found. Using default settings.")
                self.config_data = defaults
                self.config_data["llm_api_key"] = "" # Ensure key is empty if no file

        except (FileNotFoundError, json.JSONDecodeError, Exception) as e:
            print(f"ConfigManager Error: Failed to load {CONFIG_FILE} - {e}", file=sys.__stderr__)
            messagebox.showwarning(
                "Config Load Error", # Needs translation if gui_app ref was passed
                f"Could not load settings from {CONFIG_FILE}.\nUsing default values.\n\nError: {e}"
            )
            self.config_data = defaults # Fallback to defaults on error
            self.config_data["llm_api_key"] = ""

        # Remove the obfuscated key from the dict we return/use internally
        self.config_data.pop("llm_api_key_obfuscated", None)
        return self.config_data

    def save_config(self, current_settings: dict):
        """Saves the provided settings dictionary to the config file."""
        print(f"ConfigManager: Saving configuration to {CONFIG_FILE}...")
        save_data = current_settings.copy() # Work on a copy

        try:
            # Obfuscate API key before saving
            api_key = save_data.get("llm_api_key", "")
            save_data["llm_api_key_obfuscated"] = self._obfuscate(api_key)
            # Remove the clear text key from the saved data
            save_data.pop("llm_api_key", None)

            print(f"  - Saving LLM: Provider={save_data.get('llm_provider')}, Model={save_data.get('llm_model')}, Key Saved={'Yes' if api_key else 'No'}")
            print(f"  - Saving Transcription: Model={save_data.get('transcription_model')}, Lang={save_data.get('transcription_language')}, GPU={save_data.get('transcription_use_gpu')}")
            print(f"  - Saving UI Language: {save_data.get('ui_language')}")

            with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
                json.dump(save_data, f, indent=4, ensure_ascii=False)
            print("ConfigManager: Configuration saved successfully.")

        except Exception as e:
            print(f"ConfigManager Error: Failed to save configuration - {e}", file=sys.__stderr__)
            # Avoid showing messagebox on close, just log error.
            # messagebox.showerror("Config Save Error", f"Could not save settings to {CONFIG_FILE}.\n\nError: {e}")

# --- END OF FILE config_manager.py ---