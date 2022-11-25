import json
import os
import re
from typing import Any, Dict, List, Optional, Text

from rasa_sdk import Action, FormValidationAction, Tracker
from rasa_sdk.events import SlotSet, AllSlotsReset
from rasa_sdk.executor import CollectingDispatcher
from rasa_sdk.types import DomainDict

from . import create_logger
from .storage import (HttpException, InMemoryStorageImpl, MeterReadingStorage)
from .utils import normalize_language_code, forward_to_agent

logger = create_logger("actions")
STORAGE = os.getenv(key="STORAGE_IMPLEMENTATION", default="")
DEFAULT_LANGUAGE = os.getenv(key="DEFAULT_LANGUAGE", default="en")

storageImpl: MeterReadingStorage = InMemoryStorageImpl()
logger.info("Using {} as MeterReadingStorage".format(type(storageImpl).__name__))

class ActionOutboundSuccess(Action):
    def name(self) -> Text:
        return "action_cvg_outbound_success"

    def run(
        self, dispatcher: CollectingDispatcher, tracker: Tracker, domain: DomainDict
    ) -> List[Dict[Text, Any]]:
        logger.info("Outbound was successful.")
        return []

# Figure out, which language should be used to answer. See domain.yml, where the "language" slot is used.
class ActionDetectLanguage(Action):
    def name(self) -> Text:
        return "action_detect_language"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        for e in tracker.events[::-1]:
            try:
                if e["event"] == "user":
                    return [SlotSet("language", normalize_language_code(e["metadata"]["cvg_body"]["language"]))]
            except (KeyError, TypeError):
                pass
        try:
            return [SlotSet("language", normalize_language_code(tracker.slots["session_started_metadata"]["cvg_body"]["language"]))]
        except (KeyError, TypeError) as e:
            logger.warning(f"Failed to detect language. Falling back to default language: {DEFAULT_LANGUAGE}.\nDumping all Events: {json.dumps(tracker.events)}")
            logger.warning(f"Furthermore, the session_started_metadata slot does not contain the language.\n Dumping all Slots: {json.dumps(tracker.slots)}")
            return [SlotSet(key="language", value=DEFAULT_LANGUAGE)]


# Ask the user, if the meter reading for the current year should be overwritten. See required_slots for when this is asked
class ActionAskMeterReadingAlreadySet(Action):
    def name(self) -> Text:
        return "action_ask_meter_reading_already_set"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        customer = storageImpl.getCustomer(tracker.get_slot("customer_number"))
        if customer is not None:
            meter = customer.findMeterFuzzy(tracker.get_slot("meter_id"))
            if meter is not None:
                dispatcher.utter_message(
                    response="utter_ask_meter_reading_already_set",
                    meter_reading_cache=meter.meterReading,
                )  # noqa: E501
        return []

class ActionAreYouStillThere(Action):
    def name(self) -> Text:
        return "action_are_you_still_there"

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        inactivity_counter = 1 + int(tracker.get_slot("inactivity_counter"))

        if tracker.get_last_event_for(event_type="user", skip=1)["text"] != "/cvg_inactivity":
          inactivity_counter = 1 # The first time cvg_inactivity was called in a row. Make sure the counter starts with 1

        dispatcher.utter_message(response="utter_msg_you_inactive")
        if inactivity_counter > 2:
            forward_to_agent(dispatcher)
        return [SlotSet("inactivity_counter", inactivity_counter)]

class ValidateMeterReadingForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_meter_reading_form"

    async def required_slots(
        self,
        slots_mapped_in_domain: List[Text],
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Optional[List[Text]]:
        required_slots = slots_mapped_in_domain.copy()
        def remove_required_slot(slot: Text):
            if slot in required_slots:
                required_slots.remove(slot)

        customer = storageImpl.getCustomer(tracker.get_slot("customer_number"))
        if customer is None:
          return required_slots
        remove_required_slot("customer_number_correct") # customer number is definitly correct. We already found the customer.
        meter_id = tracker.get_slot("meter_id")
        meter = customer.findMeterFuzzy(meter_id)
        if meter is None:
            return required_slots
        meter_reading = tracker.get_slot("meter_reading")
        overwrite_meter_reading = tracker.get_slot(
            "meter_reading_already_set"
        )  # noqa: E501

        # If the meter reading is already set, we ask if the user wants to overwrite the current value
        if meter.meterReading is None:
            remove_required_slot("meter_reading_already_set")

        # Exactly the same, we do not need to ask if the user meant the meter which we found fuzzily
        if meter_id == meter.meterID:
            remove_required_slot("meter_id_correct_except_letter")

        if meter_reading is not None:
            meter_reading = int(meter_reading)
            meter_reading_too_large = True
            try:
                max_diff = int(meter.maxDiff)
                last_year_meter_reading = int(meter.lastYear_meterReading)
                logger.debug(f"meter_reading: {meter_reading}, max_diff: {max_diff}, last_year_meter_reading: {last_year_meter_reading}")
                if abs(meter_reading - last_year_meter_reading) <= max_diff:
                    meter_reading_too_large = False # The reading is inside the expected range. The user does not have to confirm.
            except TypeError as e:
                logger.info("maxDiff not set properly. Ignored max diff. Exception: %s", e)
            if not meter_reading_too_large:
                remove_required_slot("meter_reading_too_large")

        if overwrite_meter_reading is not None:
            if overwrite_meter_reading == False: # The user does not want to overwrite.
                required_slots = [] 
            elif overwrite_meter_reading == True:
                required_slots = ["meter_reading", "meter_reading_confirmed"]

        logger.debug("Required slots: " + str(required_slots))
        return required_slots

    # Check, if the customer number is in a correct format (6 digits)
    def validate_customer_number(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        pattern = re.compile(r'\b\d{6}\b') # A word with 6 digits: \b = word ; \d = digits

        slot_value = slot_value.replace(".", "").strip()
        matcher = pattern.search(slot_value)
        if matcher:
            slot_value = matcher.group()
        else: # Customer number is in an invalid format
            dispatcher.utter_message(response="utter_invalid_customer_number")
            return { "customer_number": None }
        return { }

    # If the user enters a customer number and says, that it is correct but we think it is invalid, there is an error in the system and we forward to call to an agent to resolve the issue.
    def validate_customer_number_correct(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value == True: # Did you enter it correctly? Yes. Something went wrong we cannot find the correctly entered customer number.
            forward_to_agent(dispatcher)
        elif slot_value != False: # If the user did not answer affirmative nor denying.
            dispatcher.utter_message(response="utter_invalid_option")
            return {"customer_number_correct": None} # Do not reset customer number. We want to ask, if the customer number is correct
        return {"customer_number": None, "customer_number_correct": None} # Rest customer number, so that user can reenter customer number.

    def validate_meter_id(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        slot_value = slot_value.replace("Ah", "A") # Some STT services detect the letter A as "Ah"
        pattern = re.compile(r'\b[A-Za-z]( ?\d){8}\b')
        
        meter_id = slot_value.replace(".", "").strip()
        matcher = pattern.search(meter_id)
        if matcher:
            meter_id = meter_id.replace(" ", "")
        
        customer = storageImpl.getCustomer(tracker.get_slot("customer_number"))
        if customer is None:
            if matcher:
                return {"meter_id": meter_id}
            dispatcher.utter_message(response="utter_msg_cannot_find_meter")
            return {"meter_id": None}
        
        for meter in customer.meters:
            if meter_id[1:] == meter.meterID[1:]:
                return {
                    "meter_id": meter_id,
                    "real_meter_id": meter.meterID,
                }
        dispatcher.utter_message(
            response="utter_msg_cannot_find_meter",
        )
        return {"meter_id": None}
            
        
    def validate_meter_id_correct_except_letter(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value == True:
            return {
                "meter_reading_already_set": None,
                "meter_id": tracker.get_slot("real_meter_id"),
            }
        elif slot_value == False:
            dispatcher.utter_message( # TODO: what should happen, when the user does not mean the meter id found by this system?
                response="utter_msg_cannot_find_meter",  # noqa: E501
            )
            return {
                "meter_id": None,
                "meter_id_correct_except_letter": None,
            }
        else:
            dispatcher.utter_message(response="utter_invalid_option")
            return {"meter_id_correct_except_letter": None}

    # Validate the response to the question, if the meter reading should be overwritten.
    def validate_meter_reading_already_set(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        customer = storageImpl.getCustomer(tracker.get_slot("customer_number"))
        if customer is None: # Unexpected. Customer was valid before.
            dispatcher.utter_message(response="utter_something_wrong")

        meter = customer.findMeterFuzzy(tracker.get_slot("meter_id"))
        if slot_value == False:  # Would you like to overwrite?
            dispatcher.utter_message(
                response="utter_meter_reading_same",
                meter_reading_cache=meter.meterReading,
            )
            dispatcher.utter_message(response="utter_goodbye")
            return { } # Call gets dropped in utter_goodbye
        elif slot_value == True:
            return {"meter_reading": None}
        else:
            dispatcher.utter_message(response="utter_invalid_option")
            return {"meter_reading_already_set": None}

    def validate_meter_reading_too_large(
      self,
      slot_value: Any,
      dispatcher: CollectingDispatcher,
      tracker: Tracker,
      domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value == False: # Is the meter reading really x kwh?
            return {"meter_reading": None, "meter_reading_too_large": None}
        elif slot_value == True:
            forward_to_agent(dispatcher)
        else:
            dispatcher.utter_message(response="utter_invalid_option")
        return {"meter_reading_too_large": None}

    def validate_meter_reading(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        # If the difference between this and last years meter reading is too large, will be checked in required_slots
        slot_value = slot_value.replace(".", "").strip()

        def checkInvalid2InARow():
          # Skip the current ask utturance, and the utturance for the error message
          # Check if the last question was also about the meter reading. If it is (this method is only called on invalid inputs), forward to an agent.
          if tracker.get_last_event_for(event_type="bot", skip=2)["metadata"]["utter_action"] == "utter_ask_meter_reading":
            forward_to_agent(dispatcher)

        try:
            meter = storageImpl.findMeter(tracker.get_slot("meter_id"))
            if meter is not None and int(slot_value) < int(meter.lastYear_meterReading):
                dispatcher.utter_message(response="utter_meter_reading_too_small")
                checkInvalid2InARow()
                return {"meter_reading": None}
            return {"meter_reading": slot_value}
        except Exception as err:
            logger.warning(err)
            dispatcher.utter_message(response="utter_invalid_meter_reading")
            checkInvalid2InARow()
            return {"meter_reading": None}

    def validate_meter_reading_confirmed(
        self,
        slot_value: Any,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: DomainDict,
    ) -> Dict[Text, Any]:
        if slot_value == True:
            return {
                "meter_reading": tracker.get_slot("meter_reading"),
                "meter_reading_confirmed": True,
            }
        elif slot_value == False: # TODO: Hm. If the user does not confirm the meter reading, should he really get redirected immidiatly? He had no chance to correct his input. We could ask him to confirm, or provide another reading.
            forward_to_agent(dispatcher)
            return {"meter_reading": None, "meter_reading_confirmed": None} # does not really matter: call gets dropped
        else:
            dispatcher.utter_message(response="utter_invalid_option")
            return {"meter_reading_confirmed": None}            

# Store the new meter reading in the storage
class ActionMeterreadingFormSubmit(Action):
    def name(self) -> Text:
        return "action_meter_reading_form_submit"

    async def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[Dict[Text, Any]]:
        meter_id = tracker.get_slot("real_meter_id")

        try:
            storageImpl.submitMeterReading(
                meter_id, tracker.get_slot("meter_reading")
            ) # Throws KeyError, if the meter_id cant be found for some reason.

            dispatcher.utter_message(response="utter_successful_meter_reading")
            logger.info(f"Meter reading {tracker.get_slot('meter_reading')} submitted for customer meter {meter_id}")

            return [AllSlotsReset()]
        except (HttpException, ValueError, KeyError) as err:
            logger.warning(err)
            dispatcher.utter_message(response="utter_something_wrong")
        finally:
            dispatcher.utter_message(response="utter_goodbye")
        return []
