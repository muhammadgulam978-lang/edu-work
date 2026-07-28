from django.contrib import admin

from .models import (
    CommunicationNotification,
    Conversation,
    ConversationParticipant,
    Message,
    MessageReaction,
    MessageReceipt,
    UserBlock,
    UserPresence,
)


admin.site.register(
    [
        Conversation,
        ConversationParticipant,
        Message,
        MessageReceipt,
        MessageReaction,
        CommunicationNotification,
        UserPresence,
        UserBlock,
    ]
)
