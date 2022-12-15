# Automate Phone Calls with a Voice Bot built with Rasa and VIER Cognitive Voice Gateway (CVG)

## Rasa and VIER CVG

[Rasa](https://rasa.com/) is the leading open-source conversational AI platform that enables both individual developers and large enterprises to build superior AI assistants and chatbots. Rasa provides the infrastructure and tools needed to build the outstanding tools and transform the way customers communicate with businesses. Rasa can be deeply customized down to levels not possible with other platforms due to the open sourced architecture and machine learning.

Rasa is used by millions of developers and small teams to program enterprise conversational AI applications.

[VIER Cognitive Voice Gateway](https://cognitivevoice.io/docs/) (CVG) enables access to telephony, best-in class speech-to-text (STT), text-to-speech (TTS) and contact center integration for bots built with Rasa. Thus, Rasa and VIER CVG can be used to build voice bots that can partially or fully automate the answering of calls.

VIER CVG is a cloud platform, fully operated in a carrier-grade datacenter on our own hardware in Frankfurt, Germany. For our international customers we can make VIER CVG available in our datacenters in Atlanta, Georgia, USA, and Singapore.

Rasa is available in two editions: Rasa Open Source (free) and Rasa Enterprise (commercial). Both editions can be used to build voicebots with CVG.

## Demo Voice Bot

To demonstrate how to build a voicebot with Rasa and VIER CVG we have built this little bot. This bot is designed to record the meter reading of a specific meter. For example, an electric meter or a water meter. Please note: This bot is just a little demo. Rasa (and CVG) is much more powerful, try it out yourself.

This bot assumes that you as a customer are identified by a customer number and you can have multiple meters, which are identified by a meter number or meter id. 

The meter reading is stored for each meter and can be overwritten if it is already set.

The meter reading can have a maximum difference between the current reading and the reading of last year. If for example the meter A12345678 has a maximum difference of 1000 and the meter reading of last year is 5000, you cannot set the reading for the current year to more than 6000. 6001 is invalid, 6000 is valid.


# Call the Bot running in our Infrastructure

To make it easy for you to get a very first experience we run this simple bot in our infrastructure. 

## Phone Numbers to call

You can call this bot 
* via +442045863834 or sip:+4972198619302@sip.cognitivevoice.io (English speaking bot)
* via +4969907362501 or sip:+4969907362501@sip.cognitivevoice.io (German speaking bot)

## Some Hints for a Dialog

You will be asked for a customer number.

For the in memory storage (default), each **customer number which is 6 digits long and starts with a 4**, is a valid customer number. Take note of your customer number and select one of the following **meter ID**:

  - **A39\<customer number>**
  - **B42\<customer number>**

Replace \<customer number> with your noted customer number. And take note of the meter number.

The first meter (starting with A39) has no meter reading set. It has a maximum difference of 2000 and the last year's meter reading is 1000.

The second meter (starting with B42) has the reading 38000 already set for the current year.

You will also need a meter reading. You can play around with the numbers here and see what happens.

## Sample input Data 

If you choose **45 61 23** as a customer number you may enter **B42 45 61 23** as meter ID and **38751** as meter reading.
Don't worry if the bot announces to transfer you to a human agent - for demo purposes we transfer you to another bot only.


# Development: Build Voice Bots with Rasa running in your Infrastructure

To build voice bots using Rasa (hosted by you) and VIER CVG (hosted by us in our cloud) use our VIER CVG channel provided as a [package](https://github.com/VIER-CognitiveVoice/rasa-vier-cvg). This package needs to be installed as part of your Rasa installation.

This VIER CVG channel in Rasa implements all the CVG APIs relevant for bots to provide CVGs full power to you as a Rasa developer.

The following APIs are part of the outgoing channel (from a bot perspective): [Call API](https://cognitivevoice.io/specs/), [Dialog API](https://cognitivevoice.io/specs/?urls.primaryName=Dialog%20API), [Assist API](https://cognitivevoice.io/specs/?urls.primaryName=Assist%20API), [Health API](https://cognitivevoice.io/specs/?urls.primaryName=Health%20API), [Recording API](https://cognitivevoice.io/specs/?urls.primaryName=Recording%20API).

The [Bot API](https://cognitivevoice.io/specs/?urls.primaryName=Bot%20API%20(Client)) is part the incoming channel (from a bot perspective).

## Add the VIER CVG Channel to Rasa

Follow the instructions [here](https://cognitivevoice.io/docs/conversational-ai/conversational-ai-rasa.html).

## Get your VIER CVG Account and configure your Project in CVG

Follow the instructions [here](https://cognitivevoice.io/docs/conversational-ai/conversational-ai-rasa.html#cvg).

## Have fun building Voice Bots with Rasa and CVG

Voicify your existing Rasa bot or clone this repo to start. Have fun! 

# Contact us in case of any Questions

Contact us via support@vier.ai. We are happy to learn about the great voice bots you build.
