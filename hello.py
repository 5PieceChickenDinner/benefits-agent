from openai import OpenAI

client = OpenAI()  # reads OPENAI_API_KEY from the environment automatically

response = client.responses.create(
    model="gpt-5-mini",
    input="In two sentences, what is a Health Savings Account?",
)

print(response.output_text)