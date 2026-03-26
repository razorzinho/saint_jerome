from saint_jerome.domain.liturgy import DailyLiturgy


def test_daily_liturgy_parses_nested_api_payload() -> None:
    payload = {
        "data": "25/03/2026",
        "liturgia": "Anunciacao do Senhor",
        "cor": "Branco",
        "oracoes": {
            "coleta": "Coleta de exemplo.",
            "extras": [
                {
                    "titulo": "Depois da leitura",
                    "texto": "Texto extra.",
                }
            ],
        },
        "leituras": {
            "primeiraLeitura": [
                {
                    "referencia": "Is 7,10-14",
                    "titulo": "Leitura do Livro do Profeta Isaias",
                    "texto": "Texto da leitura.",
                }
            ],
            "salmo": [
                {
                    "referencia": "Sl 39",
                    "refrao": "Eis que venho fazer, com prazer, a vossa vontade!",
                    "texto": "Texto do salmo.",
                }
            ],
        },
        "antifonas": {
            "entrada": "Antifona de entrada.",
        },
    }

    liturgy = DailyLiturgy.from_api_payload(payload)

    assert liturgy.date == "25/03/2026"
    assert liturgy.liturgy == "Anunciacao do Senhor"
    assert liturgy.prayers["coleta"] == "Coleta de exemplo."
    assert liturgy.prayer_extras[0].title == "Depois da leitura"
    assert liturgy.readings["primeiraLeitura"][0].reference == "Is 7,10-14"
    assert liturgy.readings["salmo"][0].refrain is not None
    assert liturgy.antiphons["entrada"] == "Antifona de entrada."
