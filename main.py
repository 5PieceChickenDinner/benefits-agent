from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from openai import OpenAI
from pydantic import BaseModel

import db

# How many earlier messages (user + assistant) to send to the model each turn.
HISTORY_LIMIT = 20

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about
U.S. employee health benefits, such as HSAs, FSAs, deductibles, and open enrollment.
Keep answers short and clear. If you are not sure, say so rather than guessing."""


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    yield


app = FastAPI(title="Benefits Agent", lifespan=lifespan)
client = OpenAI()


class AskRequest(BaseModel):
    question: str
    conversation_id: str | None = None


class AskResponse(BaseModel):
    conversation_id: str
    answer: str


class Message(BaseModel):
    role: str
    content: str
    created_at: str


class ConversationResponse(BaseModel):
    conversation_id: str
    messages: list[Message]


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    if req.conversation_id is None:
        conversation_id = db.create_conversation()
        history = []
    elif db.conversation_exists(req.conversation_id):
        conversation_id = req.conversation_id
        history = db.get_messages(conversation_id, limit=HISTORY_LIMIT)
    else:
        raise HTTPException(status_code=404, detail="Conversation not found")

    response = client.responses.create(
        model="gpt-5-mini",
        instructions=SYSTEM_PROMPT,
        input=[{"role": m["role"], "content": m["content"]} for m in history]
        + [{"role": "user", "content": req.question}],
    )
    answer = response.output_text

    # Saved only after the model call succeeds, so a failed call leaves no
    # unanswered question in the history.
    db.add_exchange(conversation_id, req.question, answer)
    return AskResponse(conversation_id=conversation_id, answer=answer)


@app.get("/conversations/{conversation_id}", response_model=ConversationResponse)
def get_conversation(conversation_id: str) -> ConversationResponse:
    if not db.conversation_exists(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    return ConversationResponse(
        conversation_id=conversation_id,
        messages=db.get_messages(conversation_id),
    )
