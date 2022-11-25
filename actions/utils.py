import os

from rasa_sdk.executor import CollectingDispatcher

from . import create_logger

SUPPORTED_LANGUAGES = os.getenv("SUPPORTED_LANGUAGES", "en,de").split(",")
DEFAULT_LANGUAGE = os.getenv("DEFAULT_LANGUAGE", "en")
logger = create_logger("utils")

def forward_to_agent(dispatcher: CollectingDispatcher) -> None:
    dispatcher.utter_message(response="utter_forward_to_agent")

def normalize_language_code(language_code: str) -> str:
    short_language_code = language_code[:2]
    if short_language_code not in SUPPORTED_LANGUAGES:
        logger.warning("Language code {} not in supported languages. Fallback to default language!".format(language_code))
        return DEFAULT_LANGUAGE
    return short_language_code 
