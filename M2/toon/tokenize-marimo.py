import marimo

__generated_with = "0.18.1"
app = marimo.App(width="medium")


@app.cell
def _():
    import marimo as mo
    return (mo,)


@app.cell(hide_code=True)
def _(mo):
    mo.md(r"""
    # Zerknij do pliku `HOMEWORK.md` aby zobaczyć opis zadania domowego :)
    """)
    return


@app.cell
def _():
    from tokenizers import Tokenizer
    import json
    import os

    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
    TOKENIZER_DIR = os.path.join(SCRIPT_DIR, 'tokenizers')
    SAMPLES_DIR = os.path.join(SCRIPT_DIR, 'samples')
    return SAMPLES_DIR, TOKENIZER_DIR, Tokenizer, json, os


@app.cell
def _(TOKENIZER_DIR, Tokenizer, mo, os):
    ALL_TOKENIZERS = {}

    if not os.path.isdir(TOKENIZER_DIR):
        print(f"❌ Error: Tokenizer directory not found at {TOKENIZER_DIR}")
        mo.md(f"❌ Error: Tokenizer directory not found at {TOKENIZER_DIR}")
        exit(1)

    for filename in os.listdir(TOKENIZER_DIR):
        if filename.endswith('.json'):
            key = filename[:-5]
            full_path = os.path.join(TOKENIZER_DIR, filename)
            try:
                ALL_TOKENIZERS[key] = Tokenizer.from_file(full_path)
                print(f"✅ Successfully loaded tokenizer: {key}")
            except Exception as e:
                print(f"❌ Error loading tokenizer '{key}' from '{full_path}': {e}")

    if not ALL_TOKENIZERS:
        print(f"❌ Error: No tokenizers found in {TOKENIZER_DIR}")
        exit(1)

    print(f"\n✅ Loaded {len(ALL_TOKENIZERS)} tokenizer(s): {list(ALL_TOKENIZERS.keys())}")
    return ALL_TOKENIZERS


@app.cell
def _(ALL_TOKENIZERS, SAMPLES_DIR, json, mo, os):
    SAMPLE_NAMES = ['arch', 'models', 'photos', 'placeholder', 'recipe']

    # Format name mapping for better display
    FORMAT_NAMES = {
        'json': 'JSON',
        'nows-json': 'JSON compact',
        'yaml': 'YAML',
        'toon': 'TOON'
    }

    def create_progress_bar(percentage, bar_length=20):
        """Create a progress bar using block characters"""
        filled_length = int(bar_length * percentage / 100)
        bar = '█' * filled_length + '░' * (bar_length - filled_length)
        return bar

    def generate_chart_for_sample(sample_name, token_counts):
        """Generate a chart for a single sample showing all formats"""
        if not token_counts:
            return f"{sample_name}\n  No data available\n"

        # Find minimum token count (most efficient = 100%)
        min_tokens = min(token_counts.values())

        # Sort by efficiency (lowest tokens first)
        sorted_formats = sorted(token_counts.items(), key=lambda x: x[1])

        # Build the chart
        chart = f"{sample_name}\n"
        for format_key, token_count in sorted_formats:
            percentage = (min_tokens / token_count) * 100
            bar = create_progress_bar(percentage)
            format_display = FORMAT_NAMES.get(format_key, format_key)

            # Add arrow for the most efficient format
            prefix = "→" if token_count == min_tokens else " "

            # Format: prefix format_name bar percentage (token_count)
            chart += f"{prefix} {format_display:<15} {bar}  {percentage:5.1f}% ({token_count})\n"

        return chart

    # Collect all results per tokenizer
    all_results = {}

    # Tokenize all samples with all tokenizers
    for tokenizer_name, tokenizer_instance in ALL_TOKENIZERS.items():
        print(f"\n{'='*50}")
        print(f"Tokenizer: {tokenizer_name}")
        print(f"{'='*50}")

        tokenizer_results = {}

        for SAMPLE_NAME in SAMPLE_NAMES:
            sample_data = {}

            # Load all 4 file formats
            file_path_json = os.path.join(SAMPLES_DIR, f"{SAMPLE_NAME}.json")
            try:
                with open(file_path_json, "r", encoding="utf-8") as f:
                    sample_data['json'] = f.read()
            except FileNotFoundError:
                sample_data['json'] = ""

            file_path_nows = os.path.join(SAMPLES_DIR, f"{SAMPLE_NAME}-nows.json")
            try:
                with open(file_path_nows, "r", encoding="utf-8") as f:
                    sample_data['nows-json'] = f.read()
            except FileNotFoundError:
                sample_data['nows-json'] = ""

            file_path_toon = os.path.join(SAMPLES_DIR, f"{SAMPLE_NAME}.toon")
            try:
                with open(file_path_toon, "r", encoding="utf-8") as f:
                    sample_data['toon'] = f.read()
            except FileNotFoundError:
                sample_data['toon'] = ""

            file_path_yaml = os.path.join(SAMPLES_DIR, f"{SAMPLE_NAME}.yaml")
            try:
                with open(file_path_yaml, "r", encoding="utf-8") as f:
                    sample_data['yaml'] = f.read()
            except FileNotFoundError:
                sample_data['yaml'] = ""

            if all(value == "" for value in sample_data.values()):
                print(f"--- 🚫 Skipping sample '{SAMPLE_NAME}': All required files are missing. ---")
            else:
                try:
                    encoded_json = tokenizer_instance.encode(sample_data.get('json', ''))
                    encoded_nows_json = tokenizer_instance.encode(sample_data.get('nows-json', ''))
                    encoded_toon = tokenizer_instance.encode(sample_data.get('toon', ''))
                    encoded_yaml = tokenizer_instance.encode(sample_data.get('yaml', ''))

                    token_counts = {
                        'json': len(encoded_json.ids),
                        'nows-json': len(encoded_nows_json.ids),
                        'yaml': len(encoded_yaml.ids),
                        'toon': len(encoded_toon.ids),
                    }

                    tokenizer_results[SAMPLE_NAME] = token_counts

                    print(f"--- Sample: {SAMPLE_NAME} ---")
                    print(f"Liczba tokenów json: {token_counts['json']}")
                    print(f"Liczba tokenów nows-json: {token_counts['nows-json']}")
                    print(f"Liczba tokenów yaml: {token_counts['yaml']}")
                    print(f"Liczba tokenów toon: {token_counts['toon']}")

                except Exception as e:
                    print(f"❌ Critical Error processing sample '{SAMPLE_NAME}': {e}")

        all_results[tokenizer_name] = tokenizer_results

    # Generate visual charts for all tokenizers
    output = ""

    for tokenizer_name, tokenizer_results in all_results.items():
        output += f"\n{'='*70}\n"
        output += f"## Tokenizer: {tokenizer_name}\n"
        output += f"{'='*70}\n\n"

        # Generate console chart for terminal
        console_chart = ""
        for sample_name in SAMPLE_NAMES:
            if sample_name in tokenizer_results:
                console_chart += generate_chart_for_sample(sample_name, tokenizer_results[sample_name])
                console_chart += "\n"

        # Print to console
        print(f"\n{console_chart}")

        # Add to markdown output wrapped in code block
        output += f"```\n{console_chart}```\n"

    mo.md(output)


if __name__ == "__main__":
    app.run()
