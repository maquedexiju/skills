---
name: business-card
description: Business card processing and management system. Use when Claude needs to (1) Extract information from business card images using AI vision models, (2) Add, list, search, or delete business card records, (3) Manage contact information with tags and metadata, or (4) Process multiple business card images in batch.
---

# Business Card Skill

A complete solution for processing business card images and managing contact information.

## Features

- **Image Recognition**: Extract structured data from business card images using vision AI
- **CRUD Operations**: Add, list, search, and delete business card records
- **Tagging System**: Organize contacts with custom tags
- **JSON Storage**: Simple file-based storage for easy backup and portability

## Quick Start

### 1. Recognize Business Card from Image

```bash
python scripts/recongize_business_card.py <image_path> [image_path2]
```

Extracts name, company, title, phone, email, address from business card images.

### 2. Add Business Card

```bash
python scripts/business_card_manage.py add \
  --name "张三" \
  --company "ABC公司" \
  --phone "13800138000" \
  --tags "供应商,技术" \
  --extra '{"LinkedIn": "linkedin.com/in/zhangsan", "微信": "zhangsan123"}'
```

The `--extra` option accepts a JSON string for additional custom fields (e.g., social media, notes, custom attributes).

### 3. List All Cards

```bash
python scripts/business_card_manage.py list
```

### 4. Search Cards

```bash
python scripts/business_card_manage.py search "关键词"
```

Searches across name, company, and tags.

### 5. Delete Card

```bash
python scripts/business_card_manage.py del <card_id>
```

## Data Schema

Each business card contains:
- `id`: Auto-generated unique identifier (8 chars)
- `name`: Contact name (required)
- `company`: Company name (optional)
- `title`: Job title (optional)
- `phone`: Phone number (optional)
- `email`: Email address (optional)
- `address`: Physical address (optional)
- `tags`: List of custom tags for categorization
- `extra_info`: Dictionary for additional custom fields

## Workflow: Process Business Card Image

1. Run recognition script on image file(s)
2. Review extracted JSON data
3. Add to database using `add` command with extracted fields
4. Optionally add tags for organization

## Workflow: Batch Processing

1. Place all card images in a directory
2. Process each image with recognition script
3. Parse JSON outputs
4. Add each card to database programmatically

## Configuration

### Recognition Script (`recongize_business_card.py`)

Update the following configuration before use:
- `api_key`: Your OpenAI-compatible API key
- `base_url`: Your API endpoint URL
- `MODEL_NAME`: Vision model name (e.g., "gpt-4o", "qwen3.5:9b")

The script supports multiple images in a single call for better accuracy.

### Database

- Default storage: `cards.json` in the `scripts/` directory (same location as `business_card_manage.py`)
- The database path is automatically determined by the script location, ensuring consistent storage regardless of where the script is executed from

## Dependencies

```bash
pip install openai pydantic
```

## Notes

- Recognition accuracy depends on the vision model quality and image clarity
- The recognition script outputs raw JSON - validate before adding to database
- Database is stored as JSON for easy manual editing if needed
- Card IDs are auto-generated but can be referenced for deletion
