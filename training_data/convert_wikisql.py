from datasets import load_dataset
import pandas as pd

# Load dataset
dataset = load_dataset(
    "Salesforce/wikisql",
    trust_remote_code=True
)

# WikiSQL aggregation mapping
AGG_MAP = {
    0: "SELECT",
    1: "MAX",
    2: "MIN",
    3: "COUNT",
    4: "SUM",
    5: "AVG"
}

rows = []

for split in ["train", "validation", "test"]:
    for item in dataset[split]:
        question = item["question"].strip()
        agg = item["sql"]["agg"]
        intent = AGG_MAP.get(agg, "SELECT")

        rows.append({
            "question": question,
            "intent": intent
        })

df = pd.DataFrame(rows)

print(df["intent"].value_counts())

df.to_csv("intent_dataset_wikisql.csv", index=False)

print(f"\nDone! Total rows: {len(df)}")
print("Saved as intent_dataset_wikisql.csv")