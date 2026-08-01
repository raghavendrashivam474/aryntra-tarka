# Aryntra Tarka — Sprint v1.5.2 Release Notes

## Intelligent Location Resolution

**Released:** 2026-08-02
**Sprint:** v1.5.2
**Scope:** backend/plugins/weather/ only

---

## Summary

Sprint v1.5.2 evolved the Weather Plugin from a basic live weather
integration into a location-aware production service capable of resolving
a much wider variety of real-world location queries.

All changes are fully contained within the plugin boundary.
The Runtime, Planner, Registry, API, and Frontend were not modified.

---

## New File

### backend/plugins/weather/location_resolver.py

A dedicated LocationResolver responsible for:

- Normalizing raw user input (stripping filler words)
- Geocoding using Open-Meteo with up to 10 candidates
- Scoring all candidates using exact name match, country hint,
  admin region hint, population, and positional ranking
- Returning the best match as a structured ResolvedLocation object
- Returning structured errors with suggestions on failure

---

## Modified Files

### backend/plugins/weather/tool.py

- Version bumped to 1.5.2
- Now instantiates LocationResolver alongside WeatherService
- execute() runs a two-stage pipeline:
    Stage 1: LocationResolver.resolve(raw_input)
    Stage 2: WeatherService.get_weather(resolved=resolved)
- Structured error responses for location_not_found and network_error
- did_you_mean suggestions included in error responses

### backend/plugins/weather/service.py

- get_weather() now accepts an optional pre-resolved ResolvedLocation
- When resolved is provided, internal geocoding is skipped entirely
- WeatherService is now a pure weather fetcher
- Backward compatible: if resolved is None, resolver is called internally
- confidence field added to success response

---

## Resolved Limitations from v1.5.1

| Location | v1.5.1 | v1.5.2 |
|---|---|---|
| Tokyo | Works | Works |
| London | Works | Works |
| Mumbai | Works | Works |
| Delhi | Unreliable | Resolved correctly |
| Delhi, India | Not supported | Resolved correctly |
| Paris, France | Unreliable | Resolved correctly |
| Noida | Unreliable | Resolved correctly |
| Ghaziabad | Unreliable | Resolved correctly |
| Cambridge, UK | Not supported | Resolved correctly |
| Filler word queries | Not normalized | Normalized correctly |
| Unknown locations | Generic error | Structured error with suggestions |
| Empty input | Generic error | Structured missing_input error |

---

## Scoring Algorithm

The LocationResolver scores each geocoding candidate using:

    +50  Exact city name match (case-insensitive)
    +30  Qualifier matches country name or country code
    +20  Qualifier matches admin1 region
    +15  Population bonus (logarithmic scale, capped at 1M+)
    + 5  First position bonus (Open-Meteo relevance ordering)
    -25  Qualifier present but candidate matches neither country nor admin

---

## Known Limitations

### Paris, Texas via API

When queried as "weather in Paris, Texas" through the chat API,
the Planner LLM extracts only "Paris" as the location parameter.
The qualifier "Texas" is dropped before reaching the plugin.

At the plugin level, LocationResolver correctly resolves
"Paris, Texas" to Paris, Texas, United States (conf=0.67).

Root cause: tool_metadata.py weather parameter description
instructs the LLM to extract a city name. This file is in
backend/planner/ which is outside the v1.5.2 scope boundary.

Resolution: Update weather location parameter description and
examples in tool_metadata.py in a future planner sprint to
instruct the LLM to preserve full location strings including
state and country qualifiers.

### LLM Response Fidelity

In some queries the LLM synthesises a response that does not
faithfully represent the tool output. This is a prompt-level
concern outside the plugin boundary.

---

## Regression Results

| Component | Status |
|---|---|
| Calculator | Pass |
| DateTimeTool | Pass |
| Weather Plugin Discovery | Pass |
| Weather Plugin Registration | Pass |
| Weather Plugin Health Check | Pass |
| Weather Plugin Version | 1.5.2 |
| Runtime | Unmodified |
| Planner | Unmodified |
| Registry | Unmodified |
| API | Unmodified |

---

## Architecture Validation

Sprint v1.5.2 further validates the Aryntra Tarka architectural promise:

> Capabilities become more intelligent through isolated plugin evolution,
> while the runtime, planner, registry, API, and frontend remain stable.

The LocationResolver pattern introduced in this sprint can be reused
by future plugins such as Maps, Places, Search, Delivery, and Travel.

---

## Files Changed

    backend/plugins/weather/location_resolver.py  (new)
    backend/plugins/weather/tool.py               (modified)
    backend/plugins/weather/service.py            (modified)

## Files Not Changed

    backend/runtime/      (stable)
    backend/planner/      (stable)
    backend/agent/        (stable)
    backend/api/          (stable)