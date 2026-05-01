"""
SecureBERT 2.0 Base Model Tester
================================
General-purpose tester for cisco-ai/SecureBERT2.0-base.
Feed it any alert text (raw or standardized) and inspect what comes out.

Outputs per input:
  - CLS embedding (768-dim) with basic stats
  - Top-k token predictions if [MASK] is present
  - Cosine similarity matrix when multiple alerts are stored

Usage:
  python securebert_tester.py                   # interactive mode
  python securebert_tester.py --file alerts.txt # one alert per line
"""

import argparse
import torch
import numpy as np
from transformers import AutoTokenizer, AutoModelForMaskedLM

MODEL_NAME = "cisco-ai/SecureBERT2.0-base"

# ── Helpers ──────────────────────────────────────────────────────────

def load_model():
    print(f"\nLoading {MODEL_NAME} ...")
    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)
    model = AutoModelForMaskedLM.from_pretrained(MODEL_NAME, output_hidden_states=True)
    model.eval()
    print("Model loaded.\n")
    return tokenizer, model


def run_inference(text: str, tokenizer, model):
    """Return CLS embedding and, if [MASK] present, top-k predictions."""
    inputs = tokenizer(text, return_tensors="pt", truncation=True, max_length=512)
    token_count = inputs["input_ids"].shape[1]

    with torch.no_grad():
        outputs = model(**inputs)

    # CLS embedding from last hidden state
    last_hidden = outputs.hidden_states[-1]          # (1, seq_len, 768)
    cls_embedding = last_hidden[0, 0, :].numpy()     # (768,)

    # Masked token predictions (if any)
    mask_predictions = []
    mask_token_id = tokenizer.mask_token_id
    if mask_token_id is not None:
        mask_positions = (inputs["input_ids"][0] == mask_token_id).nonzero(as_tuple=True)[0]
        logits = outputs.logits  # (1, seq_len, vocab_size)
        for pos in mask_positions:
            top_k = 10
            probs = torch.softmax(logits[0, pos], dim=-1)
            top_probs, top_ids = probs.topk(top_k)
            tokens = tokenizer.convert_ids_to_tokens(top_ids.tolist())
            mask_predictions.append(
                [(tok, prob.item()) for tok, prob in zip(tokens, top_probs)]
            )

    return cls_embedding, mask_predictions, token_count


def cosine_sim(a: np.ndarray, b: np.ndarray) -> float:
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def print_embedding_stats(emb: np.ndarray):
    print(f"  Shape : {emb.shape}")
    print(f"  Mean  : {emb.mean():.6f}")
    print(f"  Std   : {emb.std():.6f}")
    print(f"  Min   : {emb.min():.6f}")
    print(f"  Max   : {emb.max():.6f}")
    print(f"  Norm  : {np.linalg.norm(emb):.6f}")


def print_mask_predictions(predictions):
    for i, preds in enumerate(predictions):
        print(f"\n  [MASK] position {i+1} — top predictions:")
        for tok, prob in preds:
            bar = "█" * int(prob * 40)
            print(f"    {tok:<20s} {prob:.4f}  {bar}")


def print_similarity_matrix(labels, embeddings):
    n = len(embeddings)
    if n < 2:
        return
    print("\n" + "=" * 60)
    print("COSINE SIMILARITY MATRIX")
    print("=" * 60)

    # Header
    col_w = 8
    header = " " * 22
    for j in range(n):
        header += f"[{j+1}]".rjust(col_w)
    print(header)

    for i in range(n):
        tag = labels[i][:20].ljust(20)
        row = f"  {tag}  "
        for j in range(n):
            sim = cosine_sim(embeddings[i], embeddings[j])
            row += f"{sim:.4f}".rjust(col_w)
        print(row)
    print()


# ── Main loops ───────────────────────────────────────────────────────

def interactive_mode(tokenizer, model):
    print("=" * 60)
    print("SecureBERT 2.0 — Interactive Tester")
    print("=" * 60)
    print("Commands:")
    print("  Type or paste an alert     → run inference")
    print("  'sim'                      → show similarity matrix")
    print("  'clear'                    → reset stored embeddings")
    print("  'quit' / 'exit'            → stop")
    print("  Include [MASK] in text     → see token predictions")
    print("=" * 60)

    stored_labels = []
    stored_embeddings = []

    while True:
        try:
            text = input("\n[alert] >>> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            break

        if not text:
            continue
        if text.lower() in ("quit", "exit"):
            break
        if text.lower() == "sim":
            if len(stored_embeddings) < 2:
                print("  Need at least 2 alerts stored. Keep entering alerts.")
            else:
                print_similarity_matrix(stored_labels, stored_embeddings)
            continue
        if text.lower() == "clear":
            stored_labels.clear()
            stored_embeddings.clear()
            print("  Cleared all stored embeddings.")
            continue

        # Run inference
        cls_emb, mask_preds, tok_count = run_inference(text, tokenizer, model)
        idx = len(stored_embeddings) + 1
        label = f"Alert {idx}"
        stored_labels.append(label)
        stored_embeddings.append(cls_emb)

        print(f"\n── {label} ({tok_count} tokens) ──")
        print_embedding_stats(cls_emb)

        if mask_preds:
            print_mask_predictions(mask_preds)

        # Auto-show pairwise similarity with previous alert
        if len(stored_embeddings) >= 2:
            prev = stored_embeddings[-2]
            sim = cosine_sim(prev, cls_emb)
            print(f"\n  Similarity to {stored_labels[-2]}: {sim:.4f}")
            print("  (type 'sim' for full matrix)")


def file_mode(filepath, tokenizer, model):
    with open(filepath, "r") as f:
        lines = [l.strip() for l in f if l.strip()]

    print(f"Processing {len(lines)} alerts from {filepath}\n")

    labels = []
    embeddings = []
    for i, line in enumerate(lines, 1):
        cls_emb, mask_preds, tok_count = run_inference(line, tokenizer, model)
        label = f"Alert {i}"
        labels.append(label)
        embeddings.append(cls_emb)

        print(f"── {label} ({tok_count} tokens) ──")
        print(f"  Input: {line[:80]}{'...' if len(line) > 80 else ''}")
        print_embedding_stats(cls_emb)
        if mask_preds:
            print_mask_predictions(mask_preds)
        print()

    print_similarity_matrix(labels, embeddings)


# ── Entry point ──────────────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SecureBERT 2.0 Base Tester")
    parser.add_argument("--file", type=str, help="File with one alert per line")
    args = parser.parse_args()

    tokenizer, model = load_model()

    if args.file:
        file_mode(args.file, tokenizer, model)
    else:
        interactive_mode(tokenizer, model)
