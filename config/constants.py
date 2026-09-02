"""
config/constants.py

Small shared constants used across the app. Keeping these in one
place avoids magic strings scattered across pages/analytics files.
"""

DEFAULT_SUBJECTS = [
    "Python",
    "SQL",
    "Statistics",
    "Machine Learning",
    "DSA",
]

CODING_PLATFORMS = [
    "LeetCode",
    "Codeforces",
    "HackerRank",
    "GeeksforGeeks",
    "Other",
]

CODING_LANGUAGES_DEFAULT = [
    "Python",
    "Pandas",
    "NumPy",
    "SQL",
    "Other",
]

DIFFICULTY_LEVELS = ["Easy", "Medium", "Hard"]

CODING_TOPICS = [
    "Array",
    "String",
    "Linked List",
    "Stack",
    "Queue",
    "Tree",
    "Graph",
    "Dynamic Programming",
    "Greedy",
    "Sorting",
    "Searching",
    "Hashing",
    "Recursion",
    "Math",
    "Other",
]

CAREER_MILESTONE_TYPES = ["Internship", "Placement", "Hackathon", "Competition", "Job", "Other"]
CAREER_MILESTONE_STATUSES = ["Upcoming", "Achieved"]
JOB_TARGET_STATUSES = ["Ready", "In Progress", "Future", "Achieved"]

DEFAULT_DAILY_STUDY_GOAL_MINUTES = 60
DEFAULT_DAILY_PROBLEMS_GOAL = 2

# Real, well-known quotes (not AI-generated) from historical public
# figures, kept under 15 words each. One is shown on the Dashboard
# each day, picked deterministically by the date so it's the same for
# everyone that day and changes tomorrow -- see utils.helper.get_daily_quote.
# A user can override this with their own fixed quote in Settings.
DAILY_MOTIVATION = [
    ("The journey of a thousand miles begins with a single step.", "Lao Tzu"),
    ("Well begun is half done.", "Aristotle"),
    ("The secret of getting ahead is getting started.", "Mark Twain"),
    ("Whether you think you can, or you think you can't, you're right.", "Henry Ford"),
    ("I have not failed. I've just found 10,000 ways that won't work.", "Thomas Edison"),
    ("It always seems impossible until it's done.", "Nelson Mandela"),
    ("Genius is one percent inspiration and ninety-nine percent perspiration.", "Thomas Edison"),
    ("Believe you can and you're halfway there.", "Theodore Roosevelt"),
    ("It does not matter how slowly you go if you do not stop.", "Confucius"),
    ("Success is the sum of small efforts, repeated day in and day out.", "Robert Collier"),
    ("Try not to become a person of success, but a person of value.", "Albert Einstein"),
    ("What we think, we become.", "Buddha"),
    ("The only limit to our realization of tomorrow is our doubts of today.", "Franklin D. Roosevelt"),
    ("Do what you can, with what you have, where you are.", "Theodore Roosevelt"),
    ("Little strokes fell great oaks.", "Benjamin Franklin"),
    ("By failing to prepare, you are preparing to fail.", "Benjamin Franklin"),
    ("Energy and persistence conquer all things.", "Benjamin Franklin"),
    ("The pessimist sees difficulty in every opportunity; the optimist sees opportunity in every difficulty.", "Winston Churchill"),
    ("Continuous effort, not strength or intelligence, is the key to unlocking our potential.", "Winston Churchill"),
    ("Success is not final, failure is not fatal: courage to continue counts most.", "Winston Churchill"),
    ("Optimism is the faith that leads to achievement.", "Helen Keller"),
    ("The most difficult thing is the decision to act; the rest is merely tenacity.", "Amelia Earhart"),
    ("It's not whether you get knocked down; it's whether you get up.", "Vince Lombardi"),
    ("The way to get started is to quit talking and begin doing.", "Walt Disney"),
    ("I am a slow walker, but I never walk back.", "Abraham Lincoln"),
    ("Nothing in life is to be feared, it is only to be understood.", "Marie Curie"),
]
