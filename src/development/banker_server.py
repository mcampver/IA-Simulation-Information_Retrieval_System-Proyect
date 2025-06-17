import os
import dotenv

from gpt4all import GPT4All
from fastapi import FastAPI, Request
from argo import ChatAgent, LLM, Message, Context

# 1. Carga variables de entorno
dotenv.load_dotenv()
MODEL_PATH = os.getenv("MODEL_PATH")

# 2. Instancia el modelo local
gpt = GPT4All(model=MODEL_PATH)

def generate(prompt: str) -> str:
    # Devuelve la respuesta completa
    return gpt.generate(prompt)

# 3. Callback para streaming (opcional)
def callback(chunk: str):
    # Por simplicidad aquí no hacemos streaming HTTP, solo impresión consola
    print(chunk, end="")

# 4. Define tu agente con LLM local
agent = ChatAgent(
    name="Banker",
    description="Asistente bancario local usando GPT4All",
    llm=LLM(client=generate, callback=callback, verbose=True),
)

# 5. Skills y tools (mismo código que ya tenías)
@agent.skill
async def casual_chat(ctx: Context):
    yield await ctx.reply()

@agent.skill
async def banker(ctx: Context):
    tool = await ctx.equip()
    result = await ctx.invoke(tool)
    yield await ctx.reply(Message.tool(result))

@agent.tool
def check_balance() -> dict:
    return dict(balance=account.balance)

@agent.tool
def deposit(ammount: int) -> dict:
    return dict(balance=account.deposit(ammount), deposited=ammount)

@agent.tool
def withdraw(ammount: int) -> dict:
    try:
        return dict(balance=account.withdraw(ammount), withdrawn=ammount)
    except:
        return dict(error="Insufficient funds.", balance=account.balance)

# 6. Monta FastAPI
app = FastAPI()

@app.post("/chat")
async def chat(request: Request):
    payload = await request.json()
    user_msg = payload.get("message", "")
    # Ejecuta el agente y recoge respuesta completa
    response = ""
    async for chunk in agent.chat(user_msg):  # asume que .chat() es un async generator
        response += chunk
    return {"response": response}
