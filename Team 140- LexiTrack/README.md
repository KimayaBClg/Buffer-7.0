1. Problem Statement:
LexiTrack solves the problem of missed legal deadlines buried in complex, jargon-heavy documents. The system automates reminders by seamlessly synchronizing deadlines with Google Calendar and Classroom APIs. This ensures compliance and reduces risks, providing users with a smart, proactive management tool for their commitments.

DSA Used:
LexiTrack uses several basic data structures to handle documents smoothly. A Queue is used to manage file uploads — when a file is uploaded, it is added to the queue and a background thread processes it one by one, so the app doesn't slow down during uploads. All document records are stored in a List, with the newest document always added to the front so the latest files appear first. Each document's details (name, subject, dates, etc.) are stored as a Dictionary, allowing fast and easy access to any field by name. To remove duplicate dates found in a document, the program uses the dictionary's key-uniqueness property, which automatically keeps only one copy of each date. Finally, when the app needs to find a specific document — such as to delete it or open its calendar links — it uses a simple Linear Search through the list, which works well since the number of documents stored is small.

Video link:
https://drive.google.com/file/d/1lWaqM4G6pXguDhPdECGQTXBYvmgFlCab/view?usp=sharing
