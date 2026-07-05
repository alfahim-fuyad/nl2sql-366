"""
generate_dataset.py

Generates a synthetic intent-classification dataset for NL2SQL training.
Covers 50+ domain vocabularies across subjects, columns, values, and locations.

Output: training_data/intent_dataset.csv  (columns: question, intent)
"""

import csv
import random

random.seed(42)

# ---------- Subjects — 50+ domain coverage ----------
subjects = [
    # Generic
    "records", "data", "rows", "entries", "items", "results", "reports",
    "logs", "documents", "files", "transactions", "cases", "samples",

    # Students / Education
    "students", "student records", "pupils", "learners", "graduates",
    "enrollments", "applicants", "candidates",

    # Employees / HR
    "employees", "workers", "staff", "staff members", "personnel",
    "managers", "engineers", "developers", "designers", "analysts",
    "consultants", "interns", "contractors",

    # Customers / Users
    "customers", "buyers", "clients", "users", "members", "subscribers",
    "visitors", "guests", "shoppers", "accounts",

    # Sales / Commerce
    "sales", "orders", "purchases", "transactions", "deals", "invoices",
    "receipts", "payments", "shipments", "deliveries",

    # Products / Inventory
    "products", "items", "goods", "listings", "inventory", "stock",
    "categories", "brands", "models", "variants", "sku",

    # Movies / Entertainment
    "movies", "films", "shows", "series", "episodes", "titles",
    "albums", "tracks", "songs", "artists",

    # Cars / Vehicles
    "cars", "vehicles", "automobiles", "bikes", "trucks", "vans",

    # Hospital / Healthcare
    "patients", "hospital records", "medical records", "cases",
    "diagnoses", "treatments", "prescriptions", "admissions",

    # Loans / Finance
    "loans", "loan applications", "borrowers", "accounts", "deposits",
    "withdrawals", "investments", "portfolios", "assets",

    # Hotels / Travel
    "bookings", "reservations", "hotel bookings", "stays", "rooms",
    "flights", "passengers", "travelers", "trips", "routes",

    # Sports
    "players", "athletes", "teams", "clubs", "matches", "games",
    "seasons", "tournaments", "leagues", "fixtures",

    # Other domains
    "restaurants", "listings", "properties", "houses", "apartments",
    "crimes", "accidents", "weather records", "earthquakes", "countries",
    "companies", "startups", "projects", "tasks", "tickets", "bugs",
    "reviews", "ratings", "comments", "posts", "messages",
]

# ---------- Columns — 50+ domain specific ----------
columns = [
    # Universal numeric
    "age", "price", "salary", "income", "score", "marks", "grade",
    "amount", "quantity", "discount", "tax", "rating", "rank", "level",
    "cost", "revenue", "profit", "loss", "balance", "budget", "count",
    "total", "percentage", "ratio", "index",

    # Students / Education
    "gpa", "cgpa", "semester", "department", "major", "year",
    "credits", "attendance", "fees", "scholarship",

    # Employees / HR
    "experience", "designation", "position", "performance",
    "bonus", "allowance", "hours", "overtime",
    "satisfaction", "attrition", "tenure",

    # Sales / Commerce
    "sales", "quantity_sold", "units", "region", "category",
    "market", "channel", "discount_rate", "tax_rate",

    # Products / E-commerce
    "brand", "model", "stock", "availability",
    "ram", "storage", "battery", "processor", "screen_size",

    # Movies / Entertainment
    "genre", "release_year", "runtime", "box_office",
    "imdb_rating", "votes", "language", "director",

    # Cars / Vehicles
    "mileage", "fuel_type", "transmission", "engine_cc",
    "horsepower", "torque", "doors", "seats",

    # Hospital / Healthcare
    "disease", "blood_group", "cholesterol", "blood_pressure",
    "bmi", "glucose", "insulin", "diagnosis",
    "heart_disease", "diabetes", "survived",

    # Loans / Finance
    "loan_amount", "credit_score", "loan_status", "interest_rate",
    "loan_term", "emi", "repayment", "default_rate",

    # University Admissions
    "ielts", "gre", "toefl", "admit", "research",

    # Hotels / Travel
    "nights", "adults", "children", "fare",
    "delay", "distance", "altitude", "class",

    # Weather / Environment
    "temperature", "humidity", "rainfall", "wind_speed",
    "pm25", "aqi", "co2", "emissions",

    # Sports
    "goals", "assists", "points", "rebounds", "wins", "losses",
    "draws", "appearances", "minutes", "market_value",
    "transfer_fee", "potential", "overall",

    # Generic
    "status", "type", "size", "weight", "height",
    "depth", "length", "width", "volume", "area",
    "speed", "duration", "frequency", "capacity",
    "population", "density", "altitude", "latitude", "longitude",
]

# ---------- Values ----------
values = [
    # Numbers
    "30", "50", "100", "18", "25", "60", "45", "70", "90", "120",
    "150", "200", "500", "1000", "5000", "10000",
    "0", "1", "2", "3", "4", "5", "10", "15", "20", "40", "80",
    "3.5", "3.0", "7.5", "8.0", "9.0", "2.5",
    # Boolean-like
    "true", "false", "yes", "no", "1", "0",
    # Status
    "active", "inactive", "pending", "completed", "cancelled",
    "approved", "rejected", "open", "closed", "passed", "failed",
    "admitted", "not admitted", "survived", "defaulted",
    # Priority / level
    "high", "medium", "low", "critical", "major", "minor",
    # Grades
    "A", "B", "C", "D", "F", "A+", "B+",
    # Categories
    "male", "female", "full-time", "part-time",
    "electric", "petrol", "diesel", "hybrid",
    "automatic", "manual",
    # Membership
    "gold", "silver", "platinum", "basic", "premium",
]

# ---------- Locations — Bangladesh + international cities ----------
locations = [
    "dhaka", "chittagong", "sylhet", "khulna", "rajshahi",
    "barisal", "rangpur", "mymensingh", "comilla", "noakhali",
    "cox's bazar", "tangail", "jessore", "bogra", "dinajpur",
    "new york", "los angeles", "chicago", "houston", "london",
    "paris", "berlin", "tokyo", "beijing", "mumbai", "delhi",
    "singapore", "dubai", "sydney", "toronto", "seoul",
    "bangkok", "jakarta", "moscow", "cairo", "lagos",
    "sao paulo", "buenos aires", "mexico city", "cape town",
    "north", "south", "east", "west",
    "north america", "europe", "asia", "africa",
    "region 1", "region 2", "zone a", "zone b",
]

# ---------- Prefixes ----------
prefixes = [
    "", "can you ", "could you ", "please ", "i want to ", "i need to ",
    "tell me ", "show me ", "list me ", "give me ", "find me ", "get me ",
    "do you know ", "would you ", "can you please ", "could you please ",
    "i would like to ", "is it possible to ", "could i get ",
    "i'd like to ", "i'm looking for ", "help me ", "kindly ",
]

# ---------- Condition phrases ----------
condition_phrases = [
    # Equality
    ("where {col} is {val}", "="),
    ("where {col} = {val}", "="),
    ("where {col} equals {val}", "="),
    ("where {col} exactly {val}", "="),
    ("with {col} exactly {val}", "="),
    ("with {col} equal to {val}", "="),
    ("{col} is {val}", "="),
    ("{col} equals {val}", "="),
    ("having {col} equal to {val}", "="),
    # Greater than
    ("where {col} > {val}", ">"),
    ("where {col} greater than {val}", ">"),
    ("where {col} more than {val}", ">"),
    ("where {col} above {val}", ">"),
    ("where {col} over {val}", ">"),
    ("with {col} greater than {val}", ">"),
    ("{col} greater than {val}", ">"),
    ("{col} more than {val}", ">"),
    ("{col} above {val}", ">"),
    ("having {col} > {val}", ">"),
    # Greater or equal
    ("where {col} >= {val}", ">="),
    ("where {col} at least {val}", ">="),
    ("with {col} at least {val}", ">="),
    ("{col} at least {val}", ">="),
    ("having {col} >= {val}", ">="),
    # Less than
    ("where {col} < {val}", "<"),
    ("where {col} less than {val}", "<"),
    ("where {col} below {val}", "<"),
    ("where {col} under {val}", "<"),
    ("with {col} less than {val}", "<"),
    ("{col} less than {val}", "<"),
    ("{col} below {val}", "<"),
    ("having {col} < {val}", "<"),
    # Less or equal
    ("where {col} <= {val}", "<="),
    ("where {col} at most {val}", "<="),
    ("with {col} at most {val}", "<="),
    ("{col} at most {val}", "<="),
    ("having {col} <= {val}", "<="),
    # Not equal
    ("where {col} != {val}", "!="),
    ("where {col} not equal to {val}", "!="),
    ("where {col} is not {val}", "!="),
    ("with {col} not {val}", "!="),
    ("{col} not {val}", "!="),
    # Text
    ("where {col} contains {val}", "LIKE"),
    ("where {col} like {val}", "LIKE"),
    ("with {col} containing {val}", "LIKE"),
    ("where {col} starts with {val}", "STARTS"),
    ("where {col} ends with {val}", "ENDS"),
]

# ---------- Template generation ----------
def generate_templates(intent):
    templates = set()

    if intent == "SELECT":
        verbs = [
            "show", "show me", "show all", "show me all", "show every",
            "list", "list all", "list me", "list every",
            "display", "display all", "display me all",
            "fetch", "fetch all", "fetch me",
            "retrieve", "retrieve all",
            "get", "get me", "get all", "get every",
            "find", "find me", "find all", "find every",
            "see", "see all",
            "print", "print all",
            "return", "return all",
            "give me", "give me all", "tell me all",
        ]
        questions = [
            "what are", "what are the", "who are", "who are the",
            "which are", "which are the", "which", "what",
        ]
        location_phrases = [
            "from {loc}", "in {loc}", "at {loc}", "located in {loc}",
        ]

        for v in verbs:
            templates.add(f"{v} {{subj}}")
            templates.add(f"{v} the {{subj}}")
            templates.add(f"{v} all {{subj}}")

        for cond, _ in condition_phrases:
            for v in verbs[:15]:   # top verbs to keep set manageable
                templates.add(f"{v} {{subj}} {cond}")
                templates.add(f"{v} all {{subj}} {cond}")
            for q in questions:
                templates.add(f"{q} {{subj}} {cond}")

        for loc in location_phrases:
            for v in verbs[:10]:
                templates.add(f"{v} {{subj}} {loc}")
            for q in questions:
                templates.add(f"{q} {{subj}} {loc}")

        for cond, _ in condition_phrases[:15]:
            for loc in location_phrases:
                for v in verbs[:8]:
                    templates.add(f"{v} {{subj}} {cond} {loc}")

        # Extra
        templates.update([
            "list of {subj}", "list of all {subj}", "show list of {subj}",
            "give me a list of {subj}", "all {subj}", "all the {subj}",
            "every {subj}", "a list of {subj}",
        ])

    elif intent == "COUNT":
        count_verbs = [
            "count", "count all", "count the", "count every",
            "how many", "how many of", "how many are there",
            "total number of", "number of", "total count of",
            "tell me how many", "show me how many",
            "give me the count of", "what is the count of",
            "what is the number of",
        ]
        location_phrases = [
            "from {loc}", "in {loc}", "at {loc}", "located in {loc}",
        ]

        for v in count_verbs:
            templates.add(f"{v} {{subj}}")
            templates.add(f"{v} {{subj}}?")
            for cond, _ in condition_phrases:
                templates.add(f"{v} {{subj}} {cond}")
            for loc in location_phrases:
                templates.add(f"{v} {{subj}} {loc}")
            for cond, _ in condition_phrases[:10]:
                for loc in location_phrases:
                    templates.add(f"{v} {{subj}} {cond} {loc}")

        templates.update([
            "how many {subj} are there",
            "how many {subj} exist",
            "count of {subj}",
            "count all {subj}",
            "total {subj}",
            "total number of {subj}",
            "number of {subj}",
        ])

    elif intent == "AVG":
        words = ["average", "mean", "avg"]
        location_phrases = ["from {loc}", "in {loc}", "at {loc}"]

        for w in words:
            templates.add(f"{w} {{col}}")
            templates.add(f"{w} of {{col}}")
            templates.add(f"the {w} of {{col}}")
            templates.add(f"what is the {w} of {{col}}")
            templates.add(f"what's the {w} {{col}}")
            templates.add(f"find the {w} {{col}}")
            templates.add(f"get the {w} {{col}}")
            templates.add(f"show the {w} {{col}}")
            templates.add(f"calculate the {w} {{col}}")
            templates.add(f"{w} {{col}} of {{subj}}")
            templates.add(f"the {w} {{col}} of {{subj}}")
            templates.add(f"what is the {w} {{col}} of {{subj}}")
            templates.add(f"find the {w} {{col}} of {{subj}}")
            templates.add(f"calculate {w} {{col}} of {{subj}}")
            for loc in location_phrases:
                templates.add(f"{w} {{col}} {loc}")
                templates.add(f"the {w} {{col}} {loc}")
                templates.add(f"what is the {w} {{col}} {loc}")
            for cond, _ in condition_phrases[:10]:
                templates.add(f"{w} {{col}} of {{subj}} {cond}")
                templates.add(f"the {w} {{col}} of {{subj}} {cond}")

        templates.update([
            "average {col}", "average value of {col}",
            "mean {col}", "mean value of {col}",
            "calculate average {col}", "find average {col}",
            "what is the average {col}", "what's the average {col}",
            "average {col} of {subj}", "average {col} for {subj}",
            "mean {col} of {subj}", "avg {col}",
        ])

    elif intent == "MAX":
        words = ["maximum", "highest", "largest", "greatest", "max", "biggest", "top"]
        location_phrases = ["from {loc}", "in {loc}", "at {loc}"]

        for w in words:
            templates.add(f"{w} {{col}}")
            templates.add(f"{w} of {{col}}")
            templates.add(f"the {w} of {{col}}")
            templates.add(f"what is the {w} of {{col}}")
            templates.add(f"find the {w} {{col}}")
            templates.add(f"show the {w} {{col}}")
            templates.add(f"get the {w} {{col}}")
            templates.add(f"{w} {{col}} of {{subj}}")
            templates.add(f"the {w} {{col}} of {{subj}}")
            templates.add(f"what is the {w} {{col}} of {{subj}}")
            for loc in location_phrases:
                templates.add(f"{w} {{col}} {loc}")
                templates.add(f"the {w} {{col}} {loc}")
            for cond, _ in condition_phrases[:10]:
                templates.add(f"{w} {{col}} of {{subj}} {cond}")
                templates.add(f"the {w} {{col}} of {{subj}} {cond}")

        templates.update([
            "max {col}", "maximum {col}", "highest {col}",
            "highest value of {col}", "largest {col}", "greatest {col}",
            "biggest {col}", "maximum value of {col}",
            "find the highest {col}", "find the maximum {col}",
            "show the highest {col}", "show the maximum {col}",
            "what is the highest {col}", "what is the maximum {col}",
            "most expensive {subj}", "costliest {subj}", "most costly {subj}",
            "who has the highest {col}", "which {subj} has the highest {col}",
            "top performing {subj}", "best {subj}", "highest earning {subj}",
        ])

    elif intent == "MIN":
        words = ["minimum", "lowest", "smallest", "least", "min"]
        location_phrases = ["from {loc}", "in {loc}", "at {loc}"]

        for w in words:
            templates.add(f"{w} {{col}}")
            templates.add(f"{w} of {{col}}")
            templates.add(f"the {w} of {{col}}")
            templates.add(f"what is the {w} of {{col}}")
            templates.add(f"find the {w} {{col}}")
            templates.add(f"show the {w} {{col}}")
            templates.add(f"get the {w} {{col}}")
            templates.add(f"{w} {{col}} of {{subj}}")
            templates.add(f"the {w} {{col}} of {{subj}}")
            templates.add(f"what is the {w} {{col}} of {{subj}}")
            for loc in location_phrases:
                templates.add(f"{w} {{col}} {loc}")
                templates.add(f"the {w} {{col}} {loc}")
            for cond, _ in condition_phrases[:10]:
                templates.add(f"{w} {{col}} of {{subj}} {cond}")
                templates.add(f"the {w} {{col}} of {{subj}} {cond}")

        templates.update([
            "min {col}", "minimum {col}", "lowest {col}",
            "lowest value of {col}", "smallest {col}", "least {col}",
            "minimum value of {col}",
            "find the lowest {col}", "find the minimum {col}",
            "show the lowest {col}", "show the minimum {col}",
            "what is the lowest {col}", "what is the minimum {col}",
            "cheapest {subj}", "least expensive {subj}",
            "most affordable {subj}", "lowest priced {subj}",
            "who has the lowest {col}", "which {subj} has the lowest {col}",
            "worst performing {subj}", "least expensive {subj}",
        ])

    elif intent == "SUM":
        words = ["sum", "total", "summation", "aggregate"]
        location_phrases = ["from {loc}", "in {loc}", "at {loc}"]

        for w in words:
            templates.add(f"{w} {{col}}")
            templates.add(f"{w} of {{col}}")
            templates.add(f"the {w} of {{col}}")
            templates.add(f"what is the {w} of {{col}}")
            templates.add(f"find the {w} {{col}}")
            templates.add(f"show the {w} {{col}}")
            templates.add(f"calculate the {w} {{col}}")
            templates.add(f"{w} {{col}} of {{subj}}")
            templates.add(f"the {w} {{col}} of {{subj}}")
            templates.add(f"what is the {w} {{col}} of {{subj}}")
            templates.add(f"calculate {w} of {{col}} of {{subj}}")
            for loc in location_phrases:
                templates.add(f"{w} {{col}} {loc}")
                templates.add(f"the {w} {{col}} {loc}")
            for cond, _ in condition_phrases[:10]:
                templates.add(f"{w} {{col}} of {{subj}} {cond}")
                templates.add(f"the {w} {{col}} of {{subj}} {cond}")

        templates.update([
            "sum {col}", "sum of {col}", "sum up {col}",
            "calculate sum of {col}", "add up {col}",
            "total {col}", "total value of {col}",
            "find total {col}", "calculate total {col}",
            "what is the total {col}", "what's the total {col}",
            "aggregate {col}", "summation of {col}",
            "total {col} of {subj}", "sum of all {col}",
        ])

    return templates


# ---------- Generate all templates ----------
all_templates = {}
for intent in ["SELECT", "COUNT", "AVG", "MAX", "MIN", "SUM"]:
    templates = generate_templates(intent)
    all_templates[intent] = list(templates)
    print(f"Intent '{intent}': {len(templates)} templates ready.")

# ---------- Generate 100,000 unique examples ----------
pairs = []
seen = set()
target = 100_000
intent_counts = {intent: 0 for intent in all_templates}

print(f"\nGenerating {target:,} unique examples...")

max_attempts = target * 20
attempts = 0

while len(pairs) < target and attempts < max_attempts:
    attempts += 1
    intent = min(intent_counts, key=intent_counts.get)
    template = random.choice(all_templates[intent])

    try:
        sentence = template.format(
            subj=random.choice(subjects),
            col=random.choice(columns),
            val=random.choice(values),
            loc=random.choice(locations),
        )
    except KeyError:
        continue

    if random.random() < 0.5:
        sentence = random.choice(prefixes) + sentence

    sentence = sentence.strip()

    if sentence not in seen:
        seen.add(sentence)
        pairs.append((sentence, intent))
        intent_counts[intent] += 1
        if len(pairs) % 10000 == 0:
            print(f"  {len(pairs):,} examples done...")

random.shuffle(pairs)

# ---------- Save ----------
out_path = "training_data/intent_dataset.csv"
with open(out_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow(["question", "intent"])
    writer.writerows(pairs)

print(f"\nDone! {len(pairs):,} examples → {out_path}")
for intent, cnt in intent_counts.items():
    print(f"  {intent}: {cnt:,}")
