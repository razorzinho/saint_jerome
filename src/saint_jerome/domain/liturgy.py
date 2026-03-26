from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(slots=True, frozen=True)
class NamedText:
    title: str
    text: str


@dataclass(slots=True, frozen=True)
class ReadingOption:
    section_key: str
    reference: str
    title: str
    text: str
    refrain: str | None = None


@dataclass(slots=True, frozen=True)
class DailyLiturgy:
    date: str
    liturgy: str
    color: str
    prayers: dict[str, str]
    prayer_extras: tuple[NamedText, ...] = field(default_factory=tuple)
    readings: dict[str, tuple[ReadingOption, ...]] = field(default_factory=dict)
    antiphons: dict[str, str] = field(default_factory=dict)

    @classmethod
    def from_api_payload(cls, payload: dict) -> "DailyLiturgy":
        prayers_payload = payload.get("oracoes", {}) or {}
        readings_payload = payload.get("leituras", {}) or {}
        antiphons_payload = payload.get("antifonas", {}) or {}

        prayers: dict[str, str] = {}
        prayer_extras: list[NamedText] = []
        for key, value in prayers_payload.items():
            if key == "extras":
                for item in value or []:
                    prayer_extras.append(
                        NamedText(
                            title=str(item.get("titulo", "Extra")).strip(),
                            text=str(item.get("texto", "")).strip(),
                        )
                    )
                continue
            if value:
                prayers[key] = str(value).strip()

        readings: dict[str, tuple[ReadingOption, ...]] = {}
        for section_key, options in readings_payload.items():
            normalized_options: list[ReadingOption] = []
            for option in options or []:
                normalized_options.append(
                    ReadingOption(
                        section_key=section_key,
                        reference=str(option.get("referencia", "")).strip(),
                        title=str(option.get("titulo", "")).strip(),
                        text=str(option.get("texto", "")).strip(),
                        refrain=_optional_text(option.get("refrao")),
                    )
                )
            if normalized_options:
                readings[section_key] = tuple(normalized_options)

        antiphons = {
            key: str(value).strip()
            for key, value in antiphons_payload.items()
            if value
        }

        return cls(
            date=str(payload.get("data", "")).strip(),
            liturgy=str(payload.get("liturgia", "")).strip(),
            color=str(payload.get("cor", "")).strip(),
            prayers=prayers,
            prayer_extras=tuple(prayer_extras),
            readings=readings,
            antiphons=antiphons,
        )


@dataclass(slots=True, frozen=True)
class GuildLiturgySubscription:
    guild_id: int
    channel_id: int
    enabled: bool
    post_hour: int
    post_minute: int
    timezone: str
    include_prayers: bool = True
    include_antiphons: bool = True
    include_extras: bool = True
    last_sent_date: str | None = None


def _optional_text(value: object) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None
