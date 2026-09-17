"""
Builds a labeled training set for EU AI Act risk-tier classification.

Strictly disjoint from evals/ground_truth.json -- none of these scenarios,
industries, or phrasings overlap with the 6 classification questions used
for evaluation. That set is held out for testing only, never trained on.

Output: finetune/data/train.jsonl, finetune/data/val.jsonl
Each line: {"prompt": "<user_message>", "completion": "<expected JSON>"}
"""
import json
import random
import itertools
from pathlib import Path

random.seed(42)

OUT_DIR = Path(__file__).parent / "data"
OUT_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# Scenario templates. Each entry: (description_template, tier, article, reasoning)
# Slots get filled from INDUSTRIES / COMPANY_SIZES to create real phrasing
# variety, not just one sentence per tier copy-pasted.
# ---------------------------------------------------------------------------

INDUSTRIES = [
    "a logistics company", "a regional bank", "a hospital network", "an online retailer",
    "a manufacturing plant", "a telecom provider", "a municipal government office",
    "a staffing agency", "a car insurance company", "a university", "a fintech startup",
    "a food delivery platform", "a security firm", "a pharmaceutical company",
]

FRAMINGS = [
    "We are building {sys} to",
    "Our team wants to deploy {sys} that would",
    "A client is asking us to develop {sys} to",
    "{industry} plans to roll out {sys} to",
    "I'm evaluating a vendor's {sys}, designed to",
]

def fill(template, **kw):
    return template.format(**kw)

# --- PROHIBITED (Article 5) ---
PROHIBITED = [
    ("a social scoring system", "evaluate citizens' trustworthiness across unrelated contexts (school records, social media, shopping habits) and restrict their access to public services based on the resulting score",
     "Article 5", "Social scoring of individuals across unrelated contexts leading to detrimental treatment is a prohibited practice under Article 5."),
    ("a live facial recognition network", "continuously scan public transit stations for a watchlist of individuals, without individualized suspicion or a judicial warrant",
     "Article 5", "Real-time remote biometric identification in publicly accessible spaces for law enforcement purposes, without a targeted, warranted exception, is prohibited under Article 5."),
    ("a behavioral nudging tool", "subtly exploit the cognitive biases of elderly users to push them toward purchases they would not otherwise make, causing them financial harm",
     "Article 5", "Deploying subliminal or manipulative techniques that materially distort behavior and cause harm is a prohibited practice under Article 5."),
    ("an image-scraping tool", "build a facial recognition database by untargeted scraping of CCTV footage and social media photos without consent",
     "Article 5", "Untargeted scraping of facial images from the internet or CCTV to build a recognition database is explicitly prohibited under Article 5."),
    ("an emotion-detection camera", "monitor employee facial expressions during shifts to flag 'low engagement' for performance reviews",
     "Article 5", "Emotion inference in the workplace is a prohibited practice under Article 5, with narrow exceptions not covered by this use case."),
    ("a classroom monitoring system", "infer students' emotional states from webcam footage during exams to detect 'suspicious' behavior",
     "Article 5", "Emotion inference in educational settings is a prohibited practice under Article 5, subject to narrow safety exceptions this use case does not meet."),
    ("a biometric categorization tool", "infer people's political opinions or religious beliefs from facial images collected in public",
     "Article 5", "Biometric categorization to infer sensitive characteristics such as political or religious beliefs is prohibited under Article 5."),
    ("a policing analytics tool", "predict which named individuals are likely to commit a future crime, based solely on profiling and without any specific behavioral indicators",
     "Article 5", "Predictive policing based on profiling of individuals to predict criminal offending is a prohibited practice under Article 5."),
]

# --- HIGH-RISK (Annex III) ---
HIGH_RISK = [
    ("a CV screening tool", "automatically rank and filter job applicants before a human recruiter sees their profile",
     "Article 6, Annex III", "AI systems used in recruitment and candidate screening fall under Annex III (Employment) and are classified high-risk."),
    ("an algorithm", "decide which employees are selected for promotion or termination based on performance metrics",
     "Article 6, Annex III", "AI used for decisions on promotion or termination of employment relationships is high-risk under Annex III (Employment)."),
    ("a creditworthiness model", "decide whether to approve or deny mortgage and personal loan applications",
     "Article 6, Annex III", "AI evaluating creditworthiness for access to essential financial services is high-risk under Annex III."),
    ("an admissions algorithm", "score and rank university applicants to determine admission offers",
     "Article 6, Annex III", "AI determining access to educational institutions is high-risk under Annex III (Education)."),
    ("an exam proctoring system", "automatically flag students for cheating based on webcam and eye-tracking analysis during exams",
     "Article 6, Annex III", "AI used to evaluate students and detect prohibited behavior during assessments is high-risk under Annex III (Education)."),
    ("a triage algorithm", "prioritize which patients get faster access to emergency care based on predicted urgency",
     "Article 6, Annex III", "AI determining access to essential public healthcare services is high-risk under Annex III."),
    ("a border-control system", "assess the risk level of individuals applying for a visa or asylum based on automated profiling",
     "Article 6, Annex III", "AI used in migration, asylum, and border control risk assessments is high-risk under Annex III."),
    ("a predictive maintenance model", "control safety-critical shutoff valves in a chemical processing plant as a certified safety component",
     "Annex I", "AI functioning as a safety component of a product covered under Annex I (industrial machinery) is high-risk."),
    ("a fraud detection system", "determine eligibility for unemployment or social welfare benefits from a public agency",
     "Article 6, Annex III", "AI determining eligibility for essential public benefits and services is high-risk under Annex III."),
    ("a case-management tool", "assist judges by generating recommended sentencing ranges for criminal cases",
     "Article 6, Annex III", "AI assisting judicial authorities in interpreting facts and applying the law to a set of facts is high-risk under Annex III (Justice)."),
    ("a biometric access-control system", "verify warehouse worker identity via fingerprint before granting building access",
     "Article 6, Annex III", "AI used for biometric identification and categorisation of natural persons is high-risk under Annex III."),
    ("a dispatch-safety system", "manage traffic signal priority for emergency vehicles across a city's critical infrastructure",
     "Article 6, Annex III", "AI managing the safety of critical infrastructure such as traffic management is high-risk under Annex III."),
]

# --- LIMITED-RISK (transparency obligations) ---
LIMITED_RISK = [
    ("a customer-service chatbot", "answer common billing questions and route complex issues to a human agent",
     "Article 52", "A chatbot interacting with natural persons is limited-risk, subject to Article 52 transparency obligations (disclosing it is an AI system)."),
    ("a virtual assistant", "help website visitors find product recommendations through conversational text",
     "Article 52", "Conversational AI interacting directly with users is limited-risk, requiring disclosure under Article 52."),
    ("a video-editing tool", "generate a synthetic 'deepfake' video of a public figure for a satirical ad, with a visible disclosure label",
     "Article 52", "Generated deepfake content is limited-risk provided it carries a clear disclosure that the content is artificially generated, per Article 52."),
    ("a general-purpose foundation model", "be offered via API for third-party developers to build various downstream applications",
     "Articles 51-56", "General-purpose AI models carry their own transparency and, for high-capability models, systemic-risk obligations under Articles 51-56."),
    ("an emotion-recognition feature", "detect a user's mood from their voice to adjust background music in a consumer wellness app",
     "Article 52", "Emotion recognition outside workplace/education contexts is limited-risk, subject to a transparency obligation informing users under Article 52."),
]

# --- MINIMAL-RISK ---
MINIMAL_RISK = [
    ("a spam filter", "classify incoming emails as spam or not spam for a company mailbox",
     "", "Basic content filtering with no meaningful impact on rights or safety is minimal-risk, with no specific obligations beyond general good practice."),
    ("a recommendation engine", "suggest related products to shoppers based on browsing history",
     "", "General e-commerce product recommendations are minimal-risk."),
    ("an inventory-management tool", "forecast which warehouse items need restocking based on sales trends",
     "", "Internal inventory forecasting with no impact on individuals' rights is minimal-risk."),
    ("a video game NPC system", "control non-player character behavior to make a game more challenging",
     "", "AI used in video games for entertainment purposes is minimal-risk."),
    ("a grammar-checking tool", "suggest corrections and style improvements while employees draft internal emails",
     "", "General-purpose writing assistance with no impact on rights or safety is minimal-risk."),
    ("a scheduling assistant", "propose optimal meeting times across a team's calendars",
     "", "Internal scheduling optimization with no impact on individuals' legal rights is minimal-risk."),
    ("a predictive-text keyboard", "suggest the next word as an employee types on a company device",
     "", "Predictive text input is a low-impact productivity feature and is minimal-risk."),
    ("a music-recommendation algorithm", "curate a personalized playlist based on listening history",
     "", "Personalized content curation for entertainment is minimal-risk."),
]

def render_examples(entries, tier):
    out = []
    for sys, action, article, reasoning in entries:
        for framing in FRAMINGS:
            industry = random.choice(INDUSTRIES)
            desc = fill(framing, sys=sys, industry=industry.capitalize())
            question = f"{desc} {action}. What risk tier applies under the EU AI Act?"
            completion = {
                "tier": tier,
                "matched_article": article if article else None,
                "matched_annex_entry": article if "Annex" in article else None,
                "reasoning": reasoning,
                "confidence": "high",
            }
            out.append({"prompt": question, "completion": json.dumps(completion, ensure_ascii=False)})
    return out

def main():
    all_examples = []
    all_examples += render_examples(PROHIBITED, "prohibited")
    all_examples += render_examples(HIGH_RISK, "high-risk")
    all_examples += render_examples(LIMITED_RISK, "limited-risk")
    all_examples += render_examples(MINIMAL_RISK, "minimal-risk")

    random.shuffle(all_examples)

    # Dedupe identical prompts (can happen from random slot collisions)
    seen = set()
    deduped = []
    for ex in all_examples:
        if ex["prompt"] not in seen:
            seen.add(ex["prompt"])
            deduped.append(ex)

    n_val = max(20, int(len(deduped) * 0.1))
    val = deduped[:n_val]
    train = deduped[n_val:]

    with open(OUT_DIR / "train.jsonl", "w", encoding="utf-8") as f:
        for ex in train:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")
    with open(OUT_DIR / "val.jsonl", "w", encoding="utf-8") as f:
        for ex in val:
            f.write(json.dumps(ex, ensure_ascii=False) + "\n")

    tier_counts = {}
    for ex in deduped:
        t = json.loads(ex["completion"])["tier"]
        tier_counts[t] = tier_counts.get(t, 0) + 1

    print(f"Total examples: {len(deduped)} (train={len(train)}, val={len(val)})")
    print("Per-tier counts:", tier_counts)

if __name__ == "__main__":
    main()
