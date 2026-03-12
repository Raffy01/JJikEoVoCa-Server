from .authentication_handler import (
    authentication,
    search_user,
)
from .STT_handler import (
    handle as pronunciation_test,
    sendback as stt_sendback
)
from .dictionary_handler import (
    handle_image as dictionary_image,
    handle_text as dictionary_text,
)
from .friends_handler import (
    friend_list,
    reject_friend,
    accept_friend,
    request_friend,
    pending_requests,
    delete_friend,
)
from .wordbook_handler import (
    handle_upload as wordbook_upload,
    handle_update as wordbook_update,
    handle_delete as wordbook_delete,
    get_wordbook,
    link_subscriber as subscribe,
    cancle_subscription,
    get_subscribed_wordbooks,
    wordbook_search_and,
    wordbook_search_or,
    get_wordbook_info_by_id,
)
from .tag_handler import (
    handle_update_tag as update_tag,
    search_tag,
)
from .word_handler import (
    link_user_word_status,
    unlink_user_word_status,
    get_word_with_status,
    get_random_word,
)
from .chatbot_handler import (
    initialize_chat_service,
    handle_chat_input,
    handle_quiz_submit,
    handle_learning_analyze,
    handle_today_review,
    handle_chat_start,
    handle_business_talk,
    handle_generate_example,
)
