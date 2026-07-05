from datasets import load_dataset

dataset = load_dataset(
    "Salesforce/wikisql",
    trust_remote_code=True
)

print(dataset)
print(dataset["train"][0])