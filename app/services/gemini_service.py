from pydantic import BaseModel

from app.services.gemini_manager import gemini_manager

from app.core.config import GEMINI_MODEL

class BotResponse(BaseModel):
    reply: str
    memory_summary: str | None
    conversation_summary: str | None

class ReelReaction(BaseModel):
    reaction: str

def generate_response(
    context: str,
    user_summary: str,
    conversation_summary: str,
    old_context: str = "",
    username: str | None = None,
    is_new_user: bool = False
) -> BotResponse:
    
    input_text = f"""
        Long-term user information:
        {user_summary if user_summary else "No stored user information."}
        
        Older conversation summary:
        {conversation_summary if conversation_summary else "No older conversation summary."}
        
        Older conversation messages for summarization:
        {old_context if old_context else "No older conversation needs summarization."}
        
        Recent conversation:
        {context}
        
        Current user information:
        Instagram username: {username if username else "Unknown"}
    """

    def make_request(client):
        return client.interactions.create(
            model=GEMINI_MODEL,
            input=input_text,
            system_instruction=(
                "You are an Instagram DM assistant. "
                        
                "Reply naturally, briefly, and conversationally. "
    
                "Use all three context layers when generating the reply: "
    
                "Older conversation messages for summarization are provided only when "
                "the conversation needs compression. If they are provided, use them "
                "together with the existing older conversation summary to create a "
                "better updated conversation_summary. "
    
                "long-term user information, older conversation summary, "
                "and recent conversation. "
                
                "Recent conversation is the most important for the current topic. "
                "Use older conversation summary only when it is relevant. "
                "Use long-term user information when it helps personalize the response. "
            
                "Use the user context summary and recent conversation "
                "to maintain context. "
            
                "Use timestamps when they are useful for understanding "
                "the conversation. "
            
                "Do not invent information about the user. "
            
                "If this is a new user, their Instagram username may be available. "
                "You may use the username naturally when appropriate, "
                "but you do not have to mention it. "
            
                "If the username appears to contain a recognizable human name, "
                "you may use that apparent name naturally. "
            
                "Do not force a name from a username if it does not clearly "
                "look like a person's name. "
            
                "An apparent name inferred from a username is not a confirmed fact "
                "and must not be stored in the user context unless the user "
                "explicitly confirms or states that name. "
            
                "If the user explicitly tells you what they want to be called, "
                "that preferred name takes priority over the Instagram username. "
            
                "Match the user's language and writing style. "
                "If the user writes in Roman Bengali or Banglish, "
                "reply in Roman Bengali or Banglish. "
                "If the user writes in English, reply in English. "
                "If the user writes in Bengali script, reply in Bengali script. "
                "If the user mixes Bengali and English, naturally match that style. "
                "Do not switch language unless the user does. "
            
                "Long-term user information should contain only durable facts "
                "about the user that may be useful in future conversations. "
                
                "Only update memory_summary when there is useful new long-term "
                "information explicitly provided by the user. "
                
                "Do not store temporary statements, casual conversation, "
                "questions, jokes, emotions, or assumptions. "
                
                "Never invent user information. "
                
                "If there is no useful new long-term information, "
                "return null for memory_summary. "
                
                "Older conversation summary should contain only useful context "
                "from older parts of the conversation that may help continue "
                "the current conversation later. "
                
                "Do not simply repeat the recent conversation. "
                
                "If the existing older conversation summary is still sufficient "
                "and there is nothing important to add or change, "
                "return null for conversation_summary. "
                
                "If important older context should be added or an existing "
                "conversation summary should be updated, return the complete "
                "updated conversation summary. "
                
                "Keep both summaries compact and useful. "
                "Do not include the conversation transcript."
            ),
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": BotResponse.model_json_schema()
            }
        )
    
    interaction = gemini_manager.execute(make_request)

    return BotResponse.model_validate_json(
        interaction.output_text
    )


def analyze_reel(
    reel_title: str | None,
    reel_url: str | None
) -> ReelReaction:

    input_text = f"""
Instagram Reel metadata:

Title:
{reel_title if reel_title else "No title available"}

URL:
{reel_url if reel_url else "No URL available"}
"""
    def make_request(client):
        return client.interactions.create(
            model=GEMINI_MODEL,
            input=input_text,
            system_instruction=(
                "You choose a single emoji reaction for an Instagram Reel "
                "based ONLY on the metadata provided. "
    
                "You cannot actually watch or hear the Reel. "
                "Do not claim that you watched it. "
    
                "Infer the most likely mood or context from the title, "
                "caption-like text, hashtags, and emojis. "
    
                "Choose exactly one reaction from: "
                "❤️ 😂 🥹 💔 😳 🔥 😭 😍 🤣 👍 "
    
                "Prefer a natural reaction rather than always choosing ❤️. "
                "If the metadata is unclear, choose ❤️. "
            ),
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": ReelReaction.model_json_schema()
            }
        )
    
    interaction = gemini_manager.execute(make_request)

    return ReelReaction.model_validate_json(
        interaction.output_text
    )

