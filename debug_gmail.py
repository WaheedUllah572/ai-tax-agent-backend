from gmail_utils import fetch_messages, fetch_message_detail, get_attachments

msgs = fetch_messages()
print("Total messages:", len(msgs))

if msgs:
    msg_id = msgs[0]["id"]
    print("Testing message ID:", msg_id)

    details = fetch_message_detail(msg_id)
    attachments = get_attachments(details)

    print("Attachments found:", attachments)
else:
    print("No messages returned from Gmail API")