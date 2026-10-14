# Healthcare Chatbot Buddy

A small, responsive web app for conversational, general answers to common health questions, with relevant links to NHS sources and short-term context for follow-up questions.

## Important scope and safety

Buddy is a rule-based health-information demo—not a generative AI model, diagnostic tool, or substitute for a clinician. It matches everyday questions to a curated set of topics (cold symptoms, headaches, hydration, adult fever, sore throat, sleep, diarrhoea and vomiting, constipation, back pain, and stress), can combine related symptoms, and uses the last few messages in the current chat to respond to follow-up questions. Questions outside that set receive a clarification prompt rather than an invented answer. Conversation history is sent with requests but kept only in the browser session and is not written to a database or browser storage. Emergency phrases trigger an immediate message to contact local emergency services. These safeguards are not a replacement for emergency care or professional advice.

The included guidance is general and may not fit a particular person, country, age, pregnancy, medicines, or medical history. Review and localize the health content with qualified clinicians before offering this to patients or using it in a clinical setting. NHS links are provided as source material, not as an endorsement of this app.

## Run locally

Requires Python 3.11 or newer.

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m uvicorn app:app --reload
```

Open <http://127.0.0.1:8000>. The interactive API documentation is at <http://127.0.0.1:8000/docs>; the health check is <http://127.0.0.1:8000/api/health>.

## Run tests

```powershell
python -m unittest discover -s tests -v
```

## Deploy with Docker

```powershell
docker build -t healthcare-chatbot-buddy .
docker run --rm -p 8000:8000 healthcare-chatbot-buddy
```

The container listens on `0.0.0.0` and honors the `PORT` environment variable. A Render Blueprint is included in `render.yaml`; create a new Blueprint from this repository to deploy. No API key or external AI service is required.

## API

`POST /api/chat`

```json
{"message":"What can I do for a cold?"}
```

The request can include `history`, an array of up to 10 prior `{ "role": "user" | "assistant", "content": "..." }` turns. The response contains a `reply`, optional `topic`, `safety_level`, suggested follow-up questions, and source links. Requests must contain a non-empty message of at most 2,000 characters.
