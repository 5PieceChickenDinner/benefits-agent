from fastapi import FastAPI
from openai import OpenAI
from pydantic import BaseModel

app = FastAPI(title="Benefits Agent")
client = OpenAI()

SYSTEM_PROMPT = """You are a helpful assistant that answers questions about
U.S. employee health benefits, such as HSAs, FSAs, deductibles, and open enrollment.
Keep answers short and clear. If you are not sure, say so rather than guessing."""


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    answer: str


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest) -> AskResponse:
    response = client.responses.create(
        model="gpt-5-mini",
        instructions=SYSTEM_PROMPT,
        input=req.question,
    )
    return AskResponse(answer=response.output_text)