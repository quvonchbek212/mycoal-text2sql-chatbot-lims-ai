"""Lims AI — barcha loyihalar uchun yagona FastAPI ilova (Swagger: /docs).

Har bir loyiha o'z papkasida `APIRouter` beradi va shu yerda ulanadi.
Barcha endpointlar HTTP Basic bilan yopiq (lims_chatbot/app/auth.py).

Ishga tushirish (loyiha ildizidan):
    uvicorn main:app --reload --port 8080
"""
from __future__ import annotations

import logging

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse

from lims_chatbot.app.api import router as lims_chatbot_router
from lims_chatbot.app.auth import require_api_credentials
from lims_chatbot.app.config import get_settings

logging.basicConfig(level=logging.INFO)

DESCRIPTION = """\
LIMS bazasi bo'yicha savollarga javob beruvchi AI yordamchi (faqat o'qish).

**Avtorizatsiya.** Barcha endpointlar login va parol bilan yopiq. O'ng yuqoridagi
**Authorize** tugmasini bosing, login va parolni kiriting, so'ng **Try it out**.

**Namuna:** `POST /api/chat` →
`{"question": "Shu oy vagon hisob dalolatnomalari soni va jami vazni", "session_id": "test1", "lang": "uz"}`

`lang` — javob tili: `uz` (standart), `ru`, `en`.

Javob 10–60 soniya olishi mumkin (SQL til modeli tomonidan tuziladi).
"""

# Butun ilovaga biriktirilgan himoya: yangi router qo'shilganda ham avtomatik
# yopiq bo'ladi. /docs, /redoc, /openapi.json ochiq qoladi (Authorize uchun).
app = FastAPI(
    title="O'zbek ko'mir LIMS — AI",
    version="1.2.0",
    description=DESCRIPTION,
    dependencies=[Depends(require_api_credentials)],
    swagger_ui_parameters={"defaultModelsExpandDepth": 0},
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in get_settings().cors_allow_origins.split(",")],
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Loyihalar ---
app.include_router(lims_chatbot_router)


async def _to_docs(request) -> RedirectResponse:  # noqa: ANN001 — Starlette route (loginsiz)
    return RedirectResponse("/docs")


app.add_route("/", _to_docs, include_in_schema=False)
