from __future__ import annotations

import re
from pathlib import Path
from typing import Literal, TypedDict

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

app = FastAPI(
    title="Healthcare Chatbot Buddy",
    description="A source-backed guide to general health information. Not a diagnostic tool.",
    version="1.0.0",
)
PROJECT_DIR = Path(__file__).resolve().parent
app.mount("/static", StaticFiles(directory=PROJECT_DIR / "static"), name="static")


class ChatTurn(BaseModel):
    role: Literal["user", "assistant"]
    content: str = Field(min_length=1, max_length=2000)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    history: list[ChatTurn] = Field(default_factory=list, max_length=10)


class Source(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    reply: str
    topic: str | None = None
    safety_level: Literal["general", "urgent", "emergency"] = "general"
    suggestions: list[str] = Field(default_factory=list)
    sources: list[Source] = Field(default_factory=list)


class HealthTopic(TypedDict):
    topic: str
    keywords: list[str]
    reply: str
    seek_help: str
    suggestions: list[str]
    sources: list[Source]
    duration_reply: str


class TopicMatch(TypedDict):
    topic: HealthTopic
    score: int
    signals: list[str]


def _source(title: str, url: str) -> Source:
    return Source(title=title, url=url)


HEALTH_TOPICS: list[HealthTopic] = [
    {
        "topic": "Common cold",
        "keywords": [
            "common cold",
            "cold",
            "runny nose",
            "stuffy nose",
            "blocked nose",
            "nose is blocked",
            "sneezing",
            "sneeze",
            "cough",
            "coughing",
            "congestion",
        ],
        "reply": (
            "Cold symptoms often include a blocked or runny nose, sneezing, sore throat and "
            "cough. They usually improve on their own. Rest, drink fluids, and consider a "
            "warm drink to soothe your throat. A pharmacist can help you check whether an "
            "over-the-counter medicine is suitable for you."
        ),
        "seek_help": (
            "Contact a healthcare professional if symptoms get worse, do not improve after "
            "about 10 days, or you feel short of breath or have chest pain. Seek urgent help "
            "for severe or rapidly worsening symptoms."
        ),
        "suggestions": ["How can I soothe a sore throat?", "How can I stay hydrated?"],
        "sources": [
            _source("NHS: Common cold", "https://www.nhs.uk/conditions/common-cold/"),
        ],
        "duration_reply": (
            "A cold often takes about 1 to 2 weeks to improve. Contact a healthcare "
            "professional if it is getting worse or has not improved after about 10 days."
        ),
    },
    {
        "topic": "Headache",
        "keywords": [
            "headache",
            "head hurts",
            "my head hurts",
            "head pain",
            "migraine",
            "head is pounding",
            "pounding headache",
        ],
        "reply": (
            "For an ordinary headache, resting, drinking water, and taking a break from "
            "screens may help. If you are considering pain relief, follow the package "
            "instructions and ask a pharmacist if you are unsure whether it is suitable "
            "for you."
        ),
        "seek_help": (
            "Arrange medical advice if headaches keep returning, are getting worse, or come "
            "with symptoms that concern you. A sudden, extremely severe headache or a "
            "headache with weakness, confusion, vision loss, or trouble speaking needs "
            "urgent assessment."
        ),
        "suggestions": ["How can I stay hydrated?", "What should I do about a fever?"],
        "sources": [
            _source("NHS: Headaches", "https://www.nhs.uk/symptoms/headaches/"),
        ],
        "duration_reply": (
            "How long a headache lasts depends on its cause. If it keeps returning, gets "
            "worse, or is sudden and severe, contact a healthcare professional."
        ),
    },
    {
        "topic": "Hydration",
        "keywords": [
            "dehydration",
            "dehydrated",
            "hydrated",
            "hydration",
            "thirsty",
            "dark urine",
            "dry mouth",
            "drink water",
            "drinking water",
            "how much water",
            "water intake",
            "stay hydrated",
            "not drinking enough",
        ],
        "reply": (
            "Regularly sipping water can help you stay hydrated. Feeling thirsty, having "
            "dark yellow urine, or urinating less than usual can be signs of dehydration. "
            "If you feel sick, try small sips and gradually drink more."
        ),
        "seek_help": (
            "Get medical advice if you are unusually drowsy, persistently dizzy when "
            "standing, or urinating much less than usual. Confusion, difficulty waking, "
            "cold or pale skin, or difficulty breathing can be emergencies."
        ),
        "suggestions": ["What can I do for a headache?", "What should I do about a fever?"],
        "sources": [
            _source("NHS: Dehydration", "https://www.nhs.uk/conditions/dehydration/"),
        ],
        "duration_reply": (
            "How quickly dehydration improves depends on its cause and severity. Try small, "
            "frequent sips if you feel sick. Get medical advice for persistent dizziness, "
            "very little urine, unusual drowsiness, or inability to keep fluids down."
        ),
    },
    {
        "topic": "Fever in adults",
        "keywords": [
            "fever",
            "temperature",
            "high temperature",
            "running a temperature",
            "feeling feverish",
            "chills",
            "shivering",
        ],
        "reply": (
            "For adults, a temperature of 38°C or above is usually considered a fever, "
            "though you can feel feverish even with a lower reading. Rest, drink plenty of "
            "fluids, and stay home while you have a high temperature if possible."
        ),
        "seek_help": (
            "Contact a healthcare professional if a fever treated at home is not improving "
            "or is getting worse. This guidance is for adults; babies and children need "
            "age-specific advice from a healthcare professional."
        ),
        "suggestions": ["How can I stay hydrated?", "What can I do for a headache?"],
        "sources": [
            _source("NHS: High temperature in adults", "https://www.nhs.uk/symptoms/fever-in-adults/"),
        ],
        "duration_reply": (
            "How long a fever lasts depends on its cause. Get medical advice if it is not "
            "improving or is getting worse; children need age-specific advice."
        ),
    },
    {
        "topic": "Sore throat",
        "keywords": [
            "sore throat",
            "throat hurts",
            "my throat hurts",
            "throat pain",
            "scratchy throat",
            "painful throat",
        ],
        "reply": (
            "A warm drink may soothe a sore throat. Rest and drink fluids. Avoid giving "
            "honey to a child under 12 months, and do not use hot drinks for small children."
        ),
        "seek_help": (
            "Ask a healthcare professional if your symptoms are severe, worsening, or "
            "lasting longer than expected. Trouble breathing or being unable to swallow "
            "needs urgent medical attention."
        ),
        "suggestions": ["What can I do for a cold?", "How can I stay hydrated?"],
        "sources": [
            _source("NHS: Sore throat", "https://www.nhs.uk/symptoms/sore-throat/"),
            _source("NHS: Common cold", "https://www.nhs.uk/conditions/common-cold/"),
        ],
        "duration_reply": (
            "A sore throat commonly settles within about a week. Ask a healthcare "
            "professional if it is severe, worsening, or lasting longer."
        ),
    },
    {
        "topic": "Sleep",
        "keywords": [
            "sleep",
            "insomnia",
            "can't sleep",
            "cannot sleep",
            "trouble sleeping",
            "hard to fall asleep",
            "keep waking up",
            "waking up at night",
        ],
        "reply": (
            "A regular sleep and wake time, a relaxing wind-down routine, and a dark, quiet "
            "sleeping space may support better sleep. Try to avoid caffeine late in the day."
        ),
        "seek_help": (
            "If sleep problems persist or affect your daily life, a healthcare professional "
            "can help explore possible causes and options."
        ),
        "suggestions": ["How can I stay hydrated?", "What can I do for a headache?"],
        "sources": [
            _source("NHS: Sleep and tiredness", "https://www.nhs.uk/live-well/sleep-and-tiredness/"),
        ],
        "duration_reply": (
            "If sleep difficulties keep happening or are affecting your daily life, a "
            "healthcare professional can help you explore possible causes."
        ),
    },
    {
        "topic": "Diarrhoea and vomiting",
        "keywords": [
            "diarrhoea",
            "diarrhea",
            "loose stools",
            "watery stools",
            "vomiting",
            "throwing up",
            "being sick",
            "feel sick",
            "nausea",
            "stomach bug",
        ],
        "reply": (
            "Rest and take frequent small sips of water or other clear fluids, especially "
            "if you feel sick. Eat when you feel able. Avoid fruit juice and fizzy drinks "
            "if you have diarrhoea, as they may make it worse. A pharmacist can advise "
            "whether oral rehydration solution is appropriate."
        ),
        "seek_help": (
            "Seek medical advice if you cannot keep fluids down, notice blood, have signs "
            "of dehydration, or symptoms persist. Babies, young children, older adults, "
            "pregnant people, and people with long-term conditions may need advice sooner."
        ),
        "suggestions": ["How can I stay hydrated?", "What are signs of dehydration?"],
        "sources": [
            _source(
                "NHS: Diarrhoea and vomiting",
                "https://www.nhs.uk/symptoms/diarrhoea-and-vomiting/",
            ),
            _source("NHS: Dehydration", "https://www.nhs.uk/conditions/dehydration/"),
        ],
        "duration_reply": (
            "NHS guidance says diarrhoea often stops within 5 to 7 days and vomiting "
            "within 1 to 2 days. Seek advice sooner if you cannot keep fluids down or "
            "notice blood; seek advice if diarrhoea lasts over 7 days or vomiting over 2."
        ),
    },
    {
        "topic": "Constipation",
        "keywords": [
            "constipation",
            "constipated",
            "hard stools",
            "straining to poo",
            "straining to poop",
            "not pooping",
            "not pooing",
        ],
        "reply": (
            "For adults, gradual changes may help: drink fluids, increase fibre with "
            "fruit, vegetables, oats or whole grains, and stay gently active. Give "
            "yourself time to use the toilet and do not ignore the urge. A pharmacist "
            "can advise if these steps are not helping."
        ),
        "seek_help": (
            "Ask a healthcare professional if constipation is persistent, painful, "
            "recurrent, or worrying. This is general adult information; children need "
            "age-specific advice."
        ),
        "suggestions": ["How can I stay hydrated?", "What can I eat for more fibre?"],
        "sources": [
            _source("NHS: Constipation", "https://www.nhs.uk/conditions/constipation/"),
        ],
        "duration_reply": (
            "Lifestyle changes may take a few days, and sometimes a few weeks, to help. "
            "Ask a pharmacist or healthcare professional if it persists or worries you."
        ),
    },
    {
        "topic": "Back pain",
        "keywords": [
            "back pain",
            "backache",
            "lower back hurts",
            "my back hurts",
            "pain in my back",
        ],
        "reply": (
            "Back pain often improves over time. If you can, keep gently active and "
            "continue usual daily activities as tolerated rather than staying in bed "
            "for long periods. Ask a pharmacist or clinician before using pain medicine "
            "if you are unsure it is suitable."
        ),
        "seek_help": (
            "Seek urgent help for sudden severe or rapidly worsening back pain, or pain "
            "with fever or feeling very unwell. Emergency symptoms include weakness or "
            "numbness in both legs, loss of feeling around the genitals or anus, new "
            "bladder or bowel problems, or pain after a serious accident."
        ),
        "suggestions": ["What can I do for a headache?", "How can I sleep better?"],
        "sources": [
            _source("NHS: Back pain", "https://www.nhs.uk/conditions/back-pain/"),
        ],
        "duration_reply": (
            "Back pain often gets better within a few weeks. Seek medical advice if it "
            "does not improve after a few weeks, stops you doing daily activities, or "
            "you develop urgent warning signs."
        ),
    },
    {
        "topic": "Stress",
        "keywords": [
            "stress",
            "stressed",
            "overwhelmed",
            "feeling anxious",
            "anxiety",
            "worried all the time",
            "can't relax",
            "cannot relax",
        ],
        "reply": (
            "I'm sorry you're dealing with this. It may help to pause, take a few slow "
            "breaths, and choose one small, manageable next step. Talking with someone "
            "you trust can also help. You do not have to manage it alone."
        ),
        "seek_help": (
            "If stress or anxiety is affecting daily life or you are struggling to cope, "
            "contact a healthcare professional or mental-health service. If you might "
            "harm yourself or someone else, contact local emergency services now."
        ),
        "suggestions": ["How can I sleep better?", "I need urgent mental health help"],
        "sources": [
            _source(
                "NHS: Stress",
                "https://www.nhs.uk/mental-health/feelings-symptoms-behaviours/"
                "feelings-and-symptoms/stress/",
            ),
        ],
        "duration_reply": (
            "Stress affects people differently. If it persists, affects everyday life, "
            "or you are struggling to cope, a healthcare professional can help you find "
            "support."
        ),
    },
]

EMERGENCY_PHRASES = (
    "chest pain",
    "can't breathe",
    "cannot breathe",
    "difficulty breathing",
    "trouble breathing",
    "shortness of breath",
    "face drooping",
    "slurred speech",
    "can't speak",
    "cannot speak",
    "heart attack",
    "stroke",
    "severe bleeding",
    "choking",
    "overdose",
    "poisoning",
    "blue lips",
    "seizure",
    "unconscious",
    "not waking",
    "severe allergic reaction",
    "anaphylaxis",
    "suicidal",
    "kill myself",
    "want to die",
)

EMERGENCY_REPLY = (
    "This could be an emergency. Please contact your local emergency services now or go "
    "to the nearest emergency department. If someone is with you, ask them to stay and "
    "help. Do not wait for a chatbot response."
)

MEDICATION_TERMS = (
    "medicine",
    "medication",
    "tablet",
    "pill",
    "ibuprofen",
    "paracetamol",
    "acetaminophen",
    "antibiotic",
    "aspirin",
    "drug",
)
DOSAGE_TERMS = ("dosage", "dose", "mg")


def _normalise(text: str) -> str:
    text = text.lower().replace("\u2019", "'")
    return re.sub(r"\s+", " ", re.sub(r"[^\w\s°']", " ", text)).strip()


def _mentions_emergency(text: str) -> bool:
    for phrase in EMERGENCY_PHRASES:
        for match in re.finditer(rf"(?<!\w){re.escape(phrase)}(?!\w)", text):
            preceding_text = text[:match.start()]
            if re.search(
                r"\b(?:no|not|without|denies|deny|don't|dont|doesn't|isn't|aren't)"
                r"\b[^.!?]{0,35}$",
                preceding_text,
            ):
                continue
            return True
    return False


def _matched_signals(text: str, keywords: list[str]) -> list[str]:
    occurrences: list[tuple[int, int, str]] = []
    for keyword in keywords:
        match = re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text)
        if match:
            occurrences.append((match.start(), match.end(), keyword))

    signals: list[str] = []
    occupied_until = -1
    for start, end, keyword in sorted(occurrences, key=lambda item: (item[0], -item[1])):
        if start >= occupied_until:
            signals.append(keyword)
            occupied_until = end
    return signals


def respond_to_message(
    message: str,
    history: list[ChatTurn] | None = None,
) -> ChatResponse:
    """Return a short, source-backed answer or a conservative safety response."""
    text = _normalise(message)

    if _mentions_emergency(text):
        return ChatResponse(reply=EMERGENCY_REPLY, safety_level="emergency")

    if re.fullmatch(r"(hi|hello|hey|good morning|good afternoon|good evening)[!. ]*", text):
        return ChatResponse(
            reply=(
                "Hi, I'm Buddy. What health question can I help with? I can share general "
                "information about common symptoms and when to seek care."
            ),
            suggestions=[
                "What can I do for a cold?",
                "What can I do for a headache?",
                "How can I stay hydrated?",
            ],
        )
    if re.search(
        r"\b(what can you do|what can i ask|what can you help|help topics)\b",
        text,
    ):
        return ChatResponse(
            reply=(
                "I can share general information about colds, headaches, hydration, "
                "adult fever, sore throats, sleep, stomach bugs, constipation, back pain, "
                "and stress. I can't diagnose conditions or recommend personal medicine "
                "doses. What would you like to know?"
            ),
            suggestions=[
                "What can I do for a cold?",
                "What can I do about a stomach bug?",
                "How can I manage stress?",
            ],
        )
    if re.search(r"\b(thanks|thank you|that's helpful|that helps)\b", text):
        return ChatResponse(
            reply=(
                "You're welcome. If you have another question or a symptom changes, "
                "tell me and I'll do my best to share general guidance."
            )
        )

    asks_for_dose = any(term in text for term in DOSAGE_TERMS) or (
        ("how much" in text or "how many" in text)
        and any(term in text for term in MEDICATION_TERMS)
    )
    if asks_for_dose:
        return ChatResponse(
            reply=(
                "I can't safely recommend a medicine dose. Dosing depends on the exact "
                "medicine and personal factors such as age, other medicines, and health "
                "conditions. Follow the product label and check with a pharmacist or "
                "healthcare professional before taking it, especially for a child, during "
                "pregnancy, or if you have a long-term condition."
            ),
            safety_level="urgent",
        )

    is_follow_up = bool(
        re.search(
            r"\b(how long|what about|and then|why is it|why do i|should i worry|"
            r"is that normal|what if|how about|what should i do next)\b",
            text,
        )
    )
    match_text = text
    if is_follow_up and history:
        previous_user_message = ""
        for turn in reversed(history):
            if turn.role != "user":
                continue
            candidate = _normalise(turn.content)
            if any(
                _matched_signals(candidate, topic["keywords"])
                for topic in HEALTH_TOPICS
            ):
                previous_user_message = turn.content
                break
        if previous_user_message:
            match_text = f"{_normalise(previous_user_message)} {text}"

    matches: list[TopicMatch] = []
    for topic in HEALTH_TOPICS:
        signals = _matched_signals(match_text, topic["keywords"])
        if signals:
            matches.append(
                {
                    "topic": topic,
                    "score": sum(2 if " " in keyword else 1 for keyword in signals),
                    "signals": signals,
                }
            )

    if not matches:
        return ChatResponse(
            reply=(
                "I may be able to help. What symptom or health topic is this about, "
                "and how long has it been happening? You can describe it in your own "
                "words, but please do not include your name, address, or other identifying "
                "details. I can share general information, not diagnose or replace a "
                "healthcare professional."
            ),
            suggestions=[
                "What can I do for a cold?",
                "What can I do for a headache?",
                "How can I stay hydrated?",
            ],
        )

    matches.sort(key=lambda match: match["score"], reverse=True)
    relevant_matches = [
        match for match in matches
        if match["score"] >= 2 or match is matches[0]
    ][:3]
    topic_names = [match["topic"]["topic"] for match in relevant_matches]
    mentioned_signals = list(dict.fromkeys(
        signal
        for match in relevant_matches
        for signal in match["signals"]
    ))
    signal_summary = ", ".join(mentioned_signals[:4])
    if len(mentioned_signals) > 4:
        signal_summary += ", and other symptoms"

    child_context = bool(re.search(r"\b(child|children|baby|infant|toddler)\b", text))
    if is_follow_up and len(relevant_matches) == 1 and re.search(r"\b(how long|how many days)\b", text):
        first_topic = relevant_matches[0]["topic"]
        sections = [f"{first_topic['topic']}: {first_topic['duration_reply']}"]
    else:
        sections = [
            (
                f"{match['topic']['topic']}: {match['topic']['reply']}\n\n"
                f"When to get help: {match['topic']['seek_help']}"
            )
            for match in relevant_matches
        ]
    if child_context:
        sections.append(
            "Because you mentioned a child, please do not rely on adult guidance. "
            "Contact a pediatric healthcare professional or pharmacist for advice "
            "appropriate to the child's age."
        )
    if is_follow_up and history:
        tailored_intro = f"Following up on what you mentioned about {', '.join(topic_names).lower()}."
    else:
        tailored_intro = (
            f"You mentioned {signal_summary}. Here is general guidance related to "
            f"{' and '.join(topic_names).lower()}."
        )
    sources: list[Source] = []
    seen_source_urls: set[str] = set()
    for match in relevant_matches:
        for source in match["topic"]["sources"]:
            if source.url not in seen_source_urls:
                sources.append(source)
                seen_source_urls.add(source.url)
    suggestions = list(dict.fromkeys(
        suggestion
        for match in relevant_matches
        for suggestion in match["topic"]["suggestions"]
    ))[:3]

    return ChatResponse(
        reply=f"{tailored_intro}\n\n" + "\n\n".join(sections),
        topic=" + ".join(topic_names),
        suggestions=suggestions,
        sources=sources,
    )


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(PROJECT_DIR / "static" / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    if not request.message.strip():
        raise HTTPException(status_code=422, detail="Message must not be blank.")
    return respond_to_message(request.message, request.history)
