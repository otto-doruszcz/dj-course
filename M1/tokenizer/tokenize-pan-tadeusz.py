from tokenizers import Tokenizer
from corpora import get_corpus_file
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt

TOKENIZERS_DIR = Path("tokenizers")
TOKENIZERS = {
    tokenizer_file.stem: str(tokenizer_file)
    for tokenizer_file in TOKENIZERS_DIR.glob("*.json")
}

CORPUS_CONFIGS = [
    {"corpus_name": "WOLNELEKTURY", "glob_pattern": "pan-tadeusz-ksiega-1.txt", "output_prefix": "Pan-Tadeusz Ksiega 1"},
    {"corpus_name": "MINI", "glob_pattern": "the-pickwick-papers-gutenberg.txt", "output_prefix": "The Pickwick Papers"},
    {"corpus_name": "MINI", "glob_pattern": "fryderyk-chopin-wikipedia.txt", "output_prefix": "Fryderyk Chopin"},
]

# Collect statistics
statistics = []

# Loop through each corpus configuration
for config in CORPUS_CONFIGS:
    corpus_files = get_corpus_file(config["corpus_name"], config["glob_pattern"])

    # Read the source text
    source_txt = ""
    with open(corpus_files[0], 'r', encoding='utf-8') as f:
        source_txt = f.read()

    # Loop through all tokenizers
    for tokenizer_name, tokenizer_path in TOKENIZERS.items():
        tokenizer = Tokenizer.from_file(tokenizer_path)
        encoded = tokenizer.encode(source_txt)

        # Store statistics
        statistics.append({
            "Tokenizer": tokenizer_name,
            "Corpus": config['corpus_name'],
            "Pattern": config['glob_pattern'],
            "Output Prefix": config['output_prefix'],
            "Token Count": len(encoded.ids)
        })

        file_name = f"logs/tokenized-{config['output_prefix']}-{tokenizer_name}.log"
        with open(file_name, 'w', encoding='utf-8') as f:
            f.write(f"Liczba tokenów: {len(encoded.ids)}\n")
            f.write(f"Tokenizer: {tokenizer_name}\n")
            f.write(f"Corpus: {config['corpus_name']}\n")
            f.write(f"Pattern: {config['glob_pattern']}\n")

        print(f"Corpus: {config['corpus_name']}, Tokenizer: {tokenizer_name}, Tokens: {len(encoded.ids)}")

# Create DataFrame
df = pd.DataFrame(statistics)

# Save statistics to CSV
df.to_csv("logs/tokenization_statistics.csv", index=False)

# Create separate diagram for each corpus
for config in CORPUS_CONFIGS:
    corpus_df = df[df["Output Prefix"] == config["output_prefix"]]
    corpus_df = corpus_df.sort_values("Token Count")

    fig, ax = plt.subplots(figsize=(10, 6))
    corpus_df.plot(x="Tokenizer", y="Token Count", kind="bar", ax=ax, legend=False)
    plt.title(f"Token Count for {config['output_prefix']}")
    plt.xlabel("Tokenizer")
    plt.ylabel("Number of Tokens")
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()

    # Save with sanitized filename
    safe_filename = config['output_prefix'].replace(" ", "_").replace("-", "_")
    plt.savefig(f"logs/tokenization_{safe_filename}.png")
    plt.close()

    print(f"Diagram saved to logs/tokenization_{safe_filename}.png")

print("\nStatistics saved to logs/tokenization_statistics.csv")
print("All diagrams saved successfully")