import time
import random

from sqlalchemy.orm import Session

from database import SessionLocal
from models import User, Message

from app.services.instagram_service import (
    get_instagram_username,
    send_instagram_message,
    react_to_instagram_message,
)

from app.services.gemini_service import generate_response, analyze_reel

from app.services.conversation_service import (
    get_conversation_context,
    get_user_summary,
    get_conversation_summary,
    get_compression_context,
    save_user_summary,
    update_conversation_summary,
    update_compression_checkpoint,
)

def process_webhook(data):
    db = SessionLocal()

    try:      
        print("Incoming webhook:")
        print(data)
    
        for entry in data.get("entry", []):
            for messaging in entry.get("messaging", []):
        
                message = messaging.get("message", {})
        
                # Ignore our own outgoing messages
                if message.get("is_echo"):
                    print("Echo message ignored")
                    continue
        
                # Ignore events that are not actual messages
                if not message:
                    print("Non-message event ignored")
                    continue
        
                sender_id = messaging.get("sender", {}).get("id")
        
                user = db.query(User).filter(
                    User.instagram_id == sender_id
                ).first()
            
                is_new_user = False
                username = None
                
                if not user:
                    username = get_instagram_username(sender_id)
                
                    user = User(
                        instagram_id=sender_id,
                        name=username
                    )
                
                    db.add(user)
                    db.commit()
                    db.refresh(user)
                
                    is_new_user = True
                
                    print("New Instagram user:", username)
                
                else:
                    username = user.name
            
                print("User ID:", user.id)
    
               # Ignore our own outgoing messages
                message_id = message.get("mid")
                
                if message_id:
                    existing_message = db.query(Message).filter(
                        Message.instagram_message_id == message_id
                    ).first()
                
                    if existing_message:
                        print("Duplicate message ignored:", message_id)
                        continue
        
                
                
                # Normal text message
                text = message.get("text")
        
                if text:
                    print("Sender ID:", sender_id)
                    print("Message:", text)
                
                    user_message = Message(
                        user_id=user.id,
                        role="user",
                        content=text,
                        instagram_message_id=message_id
                    )
                
                    db.add(user_message)
                    db.commit()
    
                    context = get_conversation_context(
                        db=db,
                        user_id=user.id
                    )
                    
                    user_summary = get_user_summary(
                        db=db,
                        user_id=user.id
                    )

                    conversation_summary = get_conversation_summary(
                        db=db,
                        user_id=user.id
                    )

                    should_compress, old_context, compressed_message_id = (
                       get_compression_context(
                           db=db,
                           user_id=user.id
                       )
                    )

                    start_time = time.perf_counter()
                    
                    response = generate_response(
                        context=context,
                        user_summary=user_summary,
                        conversation_summary=conversation_summary,
                        old_context=old_context,
                        username=username,
                        is_new_user=is_new_user
                    )
                    

                    if response.memory_summary is not None:
                        save_user_summary(
                            db=db,
                            user_id=user.id,
                            summary=response.memory_summary
                        )

                    if (
                        should_compress
                        and response.conversation_summary is not None
                    ):
                        update_conversation_summary(
                            db=db,
                            user_id=user.id,
                            new_summary=response.conversation_summary
                        )
                    
                        if compressed_message_id is not None:
                            update_compression_checkpoint(
                                db=db,
                                user_id=user.id,
                                message_id=compressed_message_id
                            )
                    
                    gemini_time = time.perf_counter() - start_time
                    
                    print(f"Gemini response time: {gemini_time:.2f} seconds")

                    
                    reply = response.reply
                                
                    bot_message = Message(
                        user_id=user.id,
                        role="assistant",
                        content=reply
                    )
                
                    db.add(bot_message)
                    db.commit()
                
                    send_instagram_message(sender_id, reply)
        
                # Shared attachment
                attachments = message.get("attachments", [])
        
                for attachment in attachments:
                    if attachment.get("type") == "ig_reel":

                        payload = attachment.get("payload", {})
                    
                        reel_url = payload.get("url")
                        reel_title = payload.get("title")
                    
                        print("Sender ID:", sender_id)
                        print("Reel URL:", reel_url)
                        print("Reel title:", reel_title)
                    
                        reaction = analyze_reel(
                            reel_title=reel_title,
                            reel_url=reel_url
                        )
                    
                        print("Gemini Reel reaction:", reaction.reaction)
                    
                        time.sleep(random.randint(4, 14))
                    
                        if message_id:
                            react_to_instagram_message(
                                recipient_id=sender_id,
                                message_id=message_id,
                                reaction=reaction.reaction
                            )
    
        return 

    finally:
        db.close()