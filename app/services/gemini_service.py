from pydantic import BaseModel

from app.services.gemini_manager import gemini_manager

from app.api.prompts.prompt_builder import build_system_prompt


class AdminNotification(BaseModel):
    required: bool
    message: str | None

class BotResponse(BaseModel):
    reply: str
    memory_summary: str | None
    conversation_summary: str | None
    admin_notification: AdminNotification

class ReelReaction(BaseModel):
    reaction: str

def generate_response(
    model: str,
    context: str,
    user_summary: str | None,
    conversation_summary: str | None,
    old_context: str | None = None,
    username: str | None = None,
    is_new_user: bool = False,
    key_mode: str = "auto",
    auto_fallback: bool = True,
    settings=None,
) -> BotResponse:

    input_text = f"""
Current user information:

Instagram username:
{username if username else "Unknown"}

Recent conversation:
{context if context else "No recent conversation is available."}

Current message:
The latest user message is included in the recent conversation above.
""".strip()

    system_prompt = build_system_prompt(
        settings=settings,
        user_summary=user_summary,
        conversation_summary=conversation_summary,
        context_enabled=settings.conversation_context_enabled,
        memory_mode=settings.memory_mode,
        old_context=old_context,
        is_new_user=is_new_user,
    )

    def make_request(client):
        return client.interactions.create(
            model=model,
            input=input_text,
            system_instruction=system_prompt,
            response_format={
                "type": "text",
                "mime_type": "application/json",
                "schema": BotResponse.model_json_schema()
            }
        )

    interaction = gemini_manager.execute(
        make_request,
        key_mode=key_mode,
        auto_fallback=auto_fallback,
        model=model,
        operation="dm_reply"
    )

    return BotResponse.model_validate_json(
        interaction.output_text
    )


def analyze_reel(
    model: str,
    reel_title: str | None,
    reel_url: str | None,
    key_mode: str = "auto",
    auto_fallback: bool = True
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
            model=model,
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
    
    interaction = gemini_manager.execute(
        make_request,
        key_mode=key_mode,
        auto_fallback=auto_fallback,
        model=model,
        operation="reel_analysis"
    )

    return ReelReaction.model_validate_json(
        interaction.output_text
    )

