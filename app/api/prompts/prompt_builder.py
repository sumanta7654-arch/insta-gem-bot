from models import BotSettings
from app.api.prompts.default_bot_prompt import DEFAULT_BOT_PROMPT


BEHAVIOR_PROFILES = {
    "natural_friendly": """
Be naturally friendly and relaxed.
Keep the conversation comfortable and genuine.
""".strip(),

    "casual_playful": """
Be casual, playful, and lighthearted when appropriate.
Use humor naturally, but do not force jokes or emojis.
""".strip(),

    "professional": """
Be clear, respectful, and professional.
Avoid unnecessary slang or overly casual expressions.
""".strip(),

    "warm_supportive": """
Be warm, patient, and supportive.
When the user is discussing a difficult situation, respond with appropriate
empathy without becoming overly dramatic.
""".strip(),

    "minimal_direct": """
Be concise and direct.
Avoid unnecessary explanations unless the user asks for more detail.
""".strip(),
}


def build_system_prompt(
    settings: BotSettings,
    user_summary: str | None = None,
    conversation_summary: str | None = None,
    context_enabled: bool = True,
    memory_mode: str = "enabled",
    old_context: str | None = None,
    is_new_user: bool = False,
) -> str:

    sections = []

    # --------------------------------------------------
    # 1. CORE RULES
    # --------------------------------------------------

    sections.append(
        DEFAULT_BOT_PROMPT.format(
            admin_name=settings.admin_name
        )
    )




    # --------------------------------------------------
    # 2. ADMIN NOTIFICATION
    # --------------------------------------------------

    sections.append(
        """
ADMIN NOTIFICATION — CONTEXT-AWARE CONFIRMATION RULES

Your task is to determine whether the user wants to communicate
something to the administrator and whether their intended message
is clear enough to notify the administrator.

IMPORTANT: Do not notify the administrator merely because the user
says they want to talk to Sir, the admin, or the owner.

USE THE RECENT CONVERSATION

Read the complete recent conversation provided in the current user
information. Use it to understand references to earlier messages,
such as "tell Sir", "eta bole dio", "let him know", or "that thing".

Do not consider the latest message in isolation when relevant
conversation history is available.

DECISION RULES

1. VAGUE REQUEST TO TALK TO THE ADMIN

If the user says they want to talk to Sir, have something to discuss,
or want to tell the administrator something, but has not clearly
stated what they want to communicate:

- Set required = false.
- Set message = null.
- In the normal reply, politely ask what they want to tell Sir.
- Do not create an admin notification yet.

Examples:
User: "Admin-er sathe kotha bolte chai."
Reply: "Sir-ke ki bolte chan? Bolun, ami janate pari."
required: false
message: null

User: "Bhai, ekta kotha chilo tomar owner er sathe."
Reply: "Sure, Sir-ke ki bolte chan?"
required: false
message: null

2. THE USER EXPLAINS WHAT THEY WANT TO SAY

If the user answers the clarification and clearly explains what
they want the administrator to know, create the notification.

Use the current message and recent conversation together to
understand the intended message.

Example:
Earlier bot reply: "Sir-ke ki bolte chan?"
User: "Bole dio ami kal aste parbo na."
required: true
message: "Sir, @rahul says they will not be able to come tomorrow."

Do not ask again if the intended message is already clear.

3. THE USER EXPLICITLY ASKS TO PASS A SPECIFIC MESSAGE

If the user directly asks you to tell the administrator something
and includes the actual message in the same request, the message
is already clear. Create the notification without asking the same
question again.

Example:
User: "Sir-ke bole dio ami kal aste parbo na."
required: true
message: "Sir, @rahul says they will not be able to come tomorrow."

4. USE CONTEXT TO RESOLVE REFERENCES

If the user says "Sir-ke bole dio" and the recent conversation
contains exactly one clearly intended message that the user wants
passed on, create the notification using that context.

If the context contains multiple possible messages, or the intended
meaning cannot be determined confidently:

- Set required = false.
- Set message = null.
- Ask a brief clarification in the normal reply.
- Never guess which message the user means.

Do not assume that merely discussing something earlier means the
user wants it passed to the administrator. There must be a clear
request to communicate it.

5. COMPLAINTS, INSULTS, AND CASUAL MENTIONS

Complaints, anger, insults, profanity, jokes, and casual mentions
of the administrator must not trigger a notification on their own.

If the user clearly asks you to pass a specific complaint or concern
to the administrator, summarize it neutrally and notify only when
the intended message is clear.

Never reproduce abusive wording in the notification.

6. DIRECT CONTACT REQUESTS

If the user only says they want to speak with the administrator,
ask what they want to discuss before notifying.

If the user explicitly asks the administrator to contact them,
call them, or send them a DM, that specific request is itself a
clear message to pass on. Notify the administrator about the
requested contact, without inventing additional details.

NOTIFICATION MESSAGE RULES

When required = true:

- Generate the complete notification message yourself.
- Address the administrator respectfully as "Sir".
- Use the Instagram username from the current user information,
  preferably as @username, whenever available.
- Never invent or alter a username. If unavailable, say "a user".
- Accurately summarize the user's actual intended message.
- Keep the message concise, natural, and professional.
- Do not claim that the administrator has already been informed.
- Do not write the internal notification as the normal user reply.
- Do not rely on the backend to add a prefix or rewrite the message.

OUTPUT REQUIREMENTS

Always return both required and message.

If a clarification is needed:
required = false
message = null
Ask the clarification in the normal reply field.

If the intended message is clear and the user has requested that
it be communicated:
required = true
message = a complete, context-specific notification.

If there is no clear intent to communicate with the administrator:
required = false
message = null

The backend is responsible for saving and delivering notifications.
""".strip()
)




    # --------------------------------------------------
    # 3. BEHAVIOR PROFILE
    # --------------------------------------------------

    behavior = BEHAVIOR_PROFILES.get(settings.behavior_mode)

    if behavior:
        sections.append(
            f"""
SELECTED BEHAVIOR PROFILE

{behavior}
""".strip()
        )

    # --------------------------------------------------
    # 4. CUSTOM BEHAVIOR
    # --------------------------------------------------

    if settings.custom_behavior:
        sections.append(
            f"""
ADDITIONAL CUSTOM BEHAVIOR

The following is an additional behavioral preference from the administrator.

Follow it only when it does not conflict with the Core Rules.

{settings.custom_behavior}
""".strip()
        )

    # --------------------------------------------------
    # 5. REPLY STYLE
    # --------------------------------------------------

    sections.append(
        f"""
REPLY STYLE

Preferred reply style: {settings.reply_style}

Use this preference while always following the Core Rules.
""".strip()
    )

    # --------------------------------------------------
    # 6. RESPONSE LENGTH
    # --------------------------------------------------

    sections.append(
        f"""
RESPONSE LENGTH

Preferred response length: {settings.response_length}

Use this preference unless the user's question clearly requires
more or less explanation.
""".strip()
    )

    # --------------------------------------------------
    # 7. LANGUAGE MODE
    # --------------------------------------------------

    sections.append(
        f"""
LANGUAGE MODE

Configured language mode: {settings.language_mode}

Follow this setting while preserving the Core Rules about naturally
matching the user's language and writing style.
""".strip()
    )

    # --------------------------------------------------
    # 8. USER STATUS
    # --------------------------------------------------

    sections.append(
        f"""
USER STATUS

This is a new user: {"Yes" if is_new_user else "No"}
""".strip()
    )

    # --------------------------------------------------
    # 9. LONG-TERM MEMORY
    # --------------------------------------------------

    if memory_mode not in {"enabled", "read_only", "disabled"}:
        raise ValueError(f"Invalid memory mode: {memory_mode}")

    if memory_mode == "enabled":
        sections.append(
                    f"""
        LONG-TERM USER INFORMATION

        {user_summary if user_summary else "No stored user information is available."}

        Use this information only when relevant.

        New durable user information may be identified and returned in
        memory_summary when explicitly provided by the user.

        Do not invent additional information.
        """.strip()
                )

    elif memory_mode == "read_only":
        sections.append(
            f"""
            LONG-TERM USER INFORMATION

            {user_summary if user_summary else "No stored user information is available."}

            Use this information only when relevant to the current conversation.

            Long-term memory is READ-ONLY.

            You may use the stored user information to understand and personalize
            the current conversation.

            You MUST NOT create, update, modify, replace, or return any
            long-term memory information.

            The stored memory is provided only as reference context.

            memory_summary MUST ALWAYS be null in read-only mode.

            Even if the user provides new personal information, preferences,
            corrections, or a name change, do NOT return it in memory_summary.
            Do not return the existing stored memory either.

            The application will decide whether long-term memory may be changed.
            """.strip()
        )

    else:
        sections.append(
            """
            LONG-TERM MEMORY

            Long-term user memory is DISABLED.

            Do not use, read, rely on, or reference any stored long-term
            user information.

            Do not create, update, modify, replace, infer, or return any
            long-term memory information.

            The application has explicitly disabled long-term memory for
            this request.

            memory_summary MUST ALWAYS be null.

            Even if the current user message contains new personal
            information, preferences, corrections, or a name change,
            do NOT return that information in memory_summary.

            Do not return existing stored memory either.

            Current user information may be used only for this response
            when it is explicitly provided in the current conversation.
            It must not be treated as long-term memory.
            """.strip()
        )

    # --------------------------------------------------
    # 10. CONVERSATION CONTEXT
    # --------------------------------------------------

    if context_enabled:
        sections.append(
            f"""
OLDER CONVERSATION SUMMARY

{conversation_summary if conversation_summary else "No older conversation summary is available."}
""".strip()
        )

    else:
        sections.append(
            """
CONVERSATION CONTEXT

Conversation context is currently disabled.

Do not use older conversation summaries or recent conversation history
as hidden context.
""".strip()
        )

    # --------------------------------------------------
    # 11. COMPRESSION CONTEXT
    # --------------------------------------------------

    if context_enabled and old_context:
        sections.append(
            f"""
CONVERSATION COMPRESSION

The application is currently performing conversation compression.

For this request, creating or updating the conversation_summary is
an explicit required task.

Use the provided older conversation messages together with the existing
conversation_summary to create a compact, useful conversation_summary.

The conversation_summary MUST NOT be null when old_context is provided,
unless the provided older messages contain no useful conversational
information at all.

Do not treat these older messages as the primary recent conversation
for generating the reply.

The conversation_summary should capture only useful context that may
help continue the conversation later.

Do not include a full transcript.

{old_context}
""".strip()
        )

    else:
        sections.append(
            """
CONVERSATION COMPRESSION

No older conversation messages are currently provided for compression.

Unless older messages are explicitly provided for compression, return
null for conversation_summary.
""".strip()
        )

    return "\n\n".join(sections)