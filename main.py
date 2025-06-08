from gmail_tools import search_emails, summarize_emails

emails = search_emails.invoke("subject:google")
summary = summarize_emails.invoke({"emails": emails})  # <- wrap in dict!
print(summary)
