"""
Configurable transformer trainer (upgrade requirements #1, #2, #9).
Replaces train_bert_finetune.py.

Everything is driven by config/training_config.yaml:
  - model choice (xlm_r / mdeberta_v3 / mbert / arabert / marbert / ...)
  - hyperparameters, early stopping, warmup, fp16, grad accumulation
  - imbalance strategy (auto) and optional augmentation
  - dataset weights from the registry feed per-sample loss weights

Run:
    python sms_model/train_transformer.py                    # config's selected_model
    python sms_model/train_transformer.py --model mdeberta_v3  # override

Pipeline: validate datasets -> load -> split -> imbalance -> augment ->
tokenize -> fine-tune (best-F1 checkpointing) -> evaluate -> save.

Requires: torch, transformers, datasets (GPU strongly recommended --
Google Colab free tier is sufficient).
"""
import argparse
import os

import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import (accuracy_score, precision_recall_fscore_support,
                             roc_auc_score)

import torch
from datasets import Dataset
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          TrainingArguments, Trainer, EarlyStoppingCallback)

from config_loader import load_config, resolve_model
from sms_datasets import load_all_sms_data
from dataset_validation import validate_all
from imbalance import prepare_training_frame
from augmentation import augment_training_frame
from language_eval import evaluate_by_language, format_report


class WeightedTrainer(Trainer):
    """Trainer that applies class weights + per-sample dataset weights."""

    def __init__(self, class_weights=None, **kwargs):
        super().__init__(**kwargs)
        self._class_weights = class_weights  # tensor [w_safe, w_phishing] or None

    def compute_loss(self, model, inputs, return_outputs=False, **kwargs):
        labels = inputs.pop("labels")
        sample_w = inputs.pop("sample_weight", None)
        outputs = model(**inputs)
        logits = outputs.logits
        loss_fct = torch.nn.CrossEntropyLoss(
            weight=(self._class_weights.to(logits.device)
                    if self._class_weights is not None else None),
            reduction="none",
        )
        loss = loss_fct(logits.view(-1, logits.size(-1)), labels.view(-1))
        if sample_w is not None:
            loss = loss * sample_w.to(loss.device)
        loss = loss.mean()
        return (loss, outputs) if return_outputs else loss


def compute_metrics(eval_pred):
    logits, labels = eval_pred
    probs = torch.softmax(torch.tensor(logits), dim=1)[:, 1].numpy()
    preds = np.argmax(logits, axis=1)
    precision, recall, f1, _ = precision_recall_fscore_support(
        labels, preds, average="binary", zero_division=0)
    return {
        "accuracy": accuracy_score(labels, preds),
        "precision": precision,
        "recall": recall,
        "f1": f1,
        "roc_auc": roc_auc_score(labels, probs),
    }


def train(model_key: str = None, epochs_override: int = None,
          output_dir_override: str = None, quiet: bool = False) -> dict:
    cfg = load_config()
    model_cfg = resolve_model(cfg, model_key)
    t = cfg["training"]

    # 1. Validate datasets first (requirement #3).
    validate_all(report_path=cfg.get("validation", {}).get("report_path"),
                 fail_on_error=cfg.get("validation", {}).get("fail_on_error", True))

    # 2. Load merged data via the pluggable registry.
    df = load_all_sms_data()
    df["labels"] = (df["label"] == "phishing").astype(int)

    train_df, eval_df = train_test_split(
        df, test_size=t.get("eval_split", 0.2),
        random_state=t.get("seed", 42), stratify=df["labels"])

    # 3. Imbalance handling (training split only).
    train_df, class_w, _ = prepare_training_frame(
        train_df, cfg.get("imbalance", {}).get("strategy", "auto"),
        seed=t.get("seed", 42))
    # 4. Optional augmentation (training split only).
    train_df = augment_training_frame(train_df, cfg.get("augmentation", {}),
                                       seed=t.get("seed", 42))
    train_df["labels"] = (train_df["label"] == "phishing").astype(int)
    if "sample_weight" not in train_df.columns:
        train_df["sample_weight"] = 1.0
    train_df["sample_weight"] = train_df["sample_weight"].fillna(1.0)

    # 5. Tokenize.
    tokenizer = AutoTokenizer.from_pretrained(model_cfg["hf_name"])

    def tok(batch):
        return tokenizer(batch["message"], truncation=True,
                         padding="max_length",
                         max_length=t.get("max_length", 128))

    train_ds = Dataset.from_pandas(
        train_df[["message", "labels", "sample_weight"]].reset_index(drop=True)
    ).map(tok, batched=True)
    eval_ds = Dataset.from_pandas(
        eval_df[["message", "labels"]].reset_index(drop=True)
    ).map(tok, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        model_cfg["hf_name"], num_labels=2)

    fp16_cfg = t.get("fp16", "auto")
    use_fp16 = torch.cuda.is_available() if fp16_cfg == "auto" else bool(fp16_cfg)

    out_dir = output_dir_override or t.get(
        "output_dir", "saved_models/transformer_sms_classifier")

    # transformers v5 deprecates warmup_ratio in favour of warmup_steps.
    # Compute steps from the ratio so the YAML stays human-friendly
    # ("warm up over the first 10% of training") regardless of dataset size.
    n_epochs = epochs_override or t.get("epochs", 4)
    eff_batch = (t.get("batch_size", 16)
                 * max(t.get("gradient_accumulation_steps", 1), 1))
    steps_per_epoch = max(len(train_ds) // eff_batch, 1)
    total_steps = steps_per_epoch * n_epochs
    warmup_steps = int(total_steps * float(t.get("warmup_ratio", 0.1)))

    args = TrainingArguments(
        output_dir=os.path.join(out_dir, "checkpoints"),
        num_train_epochs=n_epochs,
        per_device_train_batch_size=t.get("batch_size", 16),
        per_device_eval_batch_size=t.get("batch_size", 16),
        gradient_accumulation_steps=t.get("gradient_accumulation_steps", 1),
        learning_rate=float(t.get("learning_rate", 2e-5)),
        warmup_steps=warmup_steps,
        weight_decay=float(t.get("weight_decay", 0.01)),
        lr_scheduler_type="linear",           # linear decay after warmup
        optim="adamw_torch",
        fp16=use_fp16,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=2,                   # checkpoint management
        load_best_model_at_end=True,          # automatic best-model selection
        metric_for_best_model=t.get("metric_for_best_model", "f1"),
        greater_is_better=True,
        logging_steps=20,
        seed=t.get("seed", 42),
        report_to=[],
        disable_tqdm=quiet,
    )

    class_weights_tensor = None
    if class_w:
        class_weights_tensor = torch.tensor(
            [class_w.get("safe", 1.0), class_w.get("phishing", 1.0)],
            dtype=torch.float)

    trainer = WeightedTrainer(
        class_weights=class_weights_tensor,
        model=model, args=args,
        train_dataset=train_ds, eval_dataset=eval_ds,
        compute_metrics=compute_metrics,
        callbacks=[EarlyStoppingCallback(
            early_stopping_patience=t.get("early_stopping_patience", 2))],
    )

    trainer.train()
    metrics = trainer.evaluate()

    print(f"\n=== Final evaluation ({model_cfg['key']} / {model_cfg['hf_name']}) ===")
    for k, v in metrics.items():
        print(f"{k}: {v:.4f}" if isinstance(v, float) else f"{k}: {v}")

    # Per-language breakdown -- the headline number is dominated by whichever
    # dataset is biggest (currently English). This shows how the model really
    # does on Arabic bank phishing, which is the actual threat.
    preds = trainer.predict(eval_ds)
    probs = torch.softmax(torch.tensor(preds.predictions), dim=1)[:, 1].numpy()
    lang_results = evaluate_by_language(
        eval_df["message"].tolist(), eval_df["labels"].values, probs)
    lang_report = format_report(lang_results, model_cfg["key"])
    print("\n" + lang_report)

    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "per_language_eval.txt"), "w",
              encoding="utf-8") as f:
        f.write(lang_report)

    trainer.save_model(out_dir)
    tokenizer.save_pretrained(out_dir)
    print(f"\nSaved fine-tuned model to {out_dir}/")
    metrics["model_key"] = model_cfg["key"]
    metrics["hf_name"] = model_cfg["hf_name"]
    metrics["per_language"] = lang_results
    return metrics


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default=None,
                         help="Model key from config (e.g. xlm_r, mdeberta_v3). "
                              "Defaults to config's selected_model.")
    parser.add_argument("--epochs", type=int, default=None)
    args = parser.parse_args()
    train(model_key=args.model, epochs_override=args.epochs)
