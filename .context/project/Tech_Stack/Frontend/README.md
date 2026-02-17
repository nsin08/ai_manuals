# Frontend Technology Guide

Version: 1.0
Date: 2026-02-17

## Purpose

Define MVP UI approach and conventions.

## MVP Stack

- Streamlit for rapid delivery
- Python client calls to FastAPI

## UI Scope

- Upload manuals
- Chat with assistant
- Show sources panel with citations
- Show ambiguity follow-up prompt when required

## UX Requirements

- Keep answer block concise and structured
- Always render citations under each answer
- Make source references clickable to doc/page when possible

## Non-goals for MVP

- Complex multi-user management
- Custom design system or advanced theming
- Real-time collaboration

## Future Path

- Optional migration to dedicated frontend framework (React/Vue) if needed post-MVP
