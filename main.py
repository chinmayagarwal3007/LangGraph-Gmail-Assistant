from gmail_tools import search_emails, summarize_emails

emails = search_emails.invoke("subject:google")  # <- use .invoke() to avoid deprecation
# summary = summarize_emails.invoke({"emails": emails})  # <- wrap in dict!
# print(summary)
