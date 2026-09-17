"""
QLoRA fine-tunes a small local model on the EU AI Act risk-tier classification
task, using finetune/data/train.jsonl (built by build_training_data.py, strictly
disjoint from evals/ground_truth.json).

Runs on a single consumer GPU (developed/tested on a 6GB RTX 4050 laptop GPU).
"""
import json
import torch
from pathlib import Path
from datasets import load_dataset
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from trl import SFTTrainer, SFTConfig

BASE_MODEL = "Qwen/Qwen2.5-1.5B-Instruct"
OUT_DIR = Path(__file__).parent / "lexpilot-classifier-lora"
DATA_DIR = Path(__file__).parent / "data"

SYSTEM_PROMPT = (
    "You must respond with ONLY valid JSON. No explanation, no markdown, no preamble.\n"
    'Schema: {"tier": "prohibited|high-risk|limited-risk|minimal-risk", '
    '"matched_article": "Article X or null", "matched_annex_entry": "string or null", '
    '"reasoning": "string", "confidence": "high|medium|low"}\n'
    "You are analyzing an AI system to classify it under the EU AI Act."
)

def format_example(ex):
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": ex["prompt"]},
        {"role": "assistant", "content": ex["completion"]},
    ]
    return {"messages": messages}

def main():
    print(f"Loading base model: {BASE_MODEL}")
    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_compute_dtype=torch.bfloat16,
        bnb_4bit_use_double_quant=True,
    )

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL,
        quantization_config=bnb_config,
        device_map="auto",
        torch_dtype=torch.bfloat16,
    )
    model = prepare_model_for_kbit_training(model)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    ds = load_dataset("json", data_files={
        "train": str(DATA_DIR / "train.jsonl"),
        "validation": str(DATA_DIR / "val.jsonl"),
    })
    ds = ds.map(format_example)

    sft_config = SFTConfig(
        output_dir=str(OUT_DIR),
        num_train_epochs=3,
        per_device_train_batch_size=2,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        bf16=True,
        logging_steps=10,
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=1,
        report_to=[],
        max_length=512,
        packing=False,
    )

    trainer = SFTTrainer(
        model=model,
        args=sft_config,
        train_dataset=ds["train"],
        eval_dataset=ds["validation"],
        processing_class=tokenizer,
    )

    print("Starting training...")
    trainer.train()

    print(f"Saving LoRA adapter to {OUT_DIR}")
    trainer.save_model(str(OUT_DIR))
    tokenizer.save_pretrained(str(OUT_DIR))

    with open(OUT_DIR / "training_meta.json", "w") as f:
        json.dump({
            "base_model": BASE_MODEL,
            "lora_config": lora_config.to_dict() if hasattr(lora_config, "to_dict") else str(lora_config),
            "train_examples": len(ds["train"]),
            "val_examples": len(ds["validation"]),
        }, f, indent=2)

    print("Done.")

if __name__ == "__main__":
    main()
