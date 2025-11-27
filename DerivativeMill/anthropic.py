import anthropic

client = anthropic.Anthropic(
    # defaults to os.environ.get("ANTHROPIC_API_KEY")
    api_key="m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",
)

message = client.messages.create(
    model="claude-sonnet-4-5-20250929",
    max_tokens=20000,
    temperature=1,
    messages=[]
)
print(message.content)