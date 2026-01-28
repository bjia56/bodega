from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import re
import frontmatter

from bodega.utils import now_utc


class TicketType(str, Enum):
    BUG = "bug"
    FEATURE = "feature"
    TASK = "task"
    EPIC = "epic"
    CHORE = "chore"


class TicketStatus(str, Enum):
    OPEN = "open"
    IN_PROGRESS = "in-progress"
    CLOSED = "closed"


@dataclass
class Ticket:
    id: str
    title: str
    type: TicketType = TicketType.TASK
    status: TicketStatus = TicketStatus.OPEN
    priority: int = 2
    assignee: Optional[str] = None
    tags: list[str] = field(default_factory=list)
    deps: list[str] = field(default_factory=list)
    links: list[str] = field(default_factory=list)
    parent: Optional[str] = None
    external_ref: Optional[str] = None
    created: datetime = field(default_factory=now_utc)
    updated: datetime = field(default_factory=now_utc)

    # Content sections (not in frontmatter)
    description: Optional[str] = None
    design: Optional[str] = None
    acceptance_criteria: Optional[str] = None
    notes: list[str] = field(default_factory=list)

    def __post_init__(self):
        """Validate ticket data after initialization."""
        # Validate priority
        if not 0 <= self.priority <= 4:
            raise ValueError(f"Priority must be 0-4, got {self.priority}")

        # Validate title
        if not self.title or not self.title.strip():
            raise ValueError("Title must not be empty")

        # Validate id pattern (allow empty for new tickets)
        if self.id:
            if not re.match(r'^[a-z]+-[a-f0-9]+$', self.id):
                raise ValueError(f"ID must match pattern '^[a-z]+-[a-f0-9]+$', got '{self.id}'")

        # Convert string enums to proper enum instances if needed
        if isinstance(self.type, str):
            self.type = TicketType(self.type)
        if isinstance(self.status, str):
            self.status = TicketStatus(self.status)

    def to_frontmatter(self) -> dict:
        """Convert ticket metadata to frontmatter dict."""
        fm = {
            "id": self.id,
            "title": self.title,
            "type": self.type.value,
            "status": self.status.value,
            "priority": self.priority,
        }

        # Add optional fields only if they have values
        if self.assignee:
            fm["assignee"] = self.assignee
        if self.tags:
            fm["tags"] = self.tags
        if self.deps:
            fm["deps"] = self.deps
        if self.links:
            fm["links"] = self.links
        if self.parent:
            fm["parent"] = self.parent
        if self.external_ref:
            fm["external_ref"] = self.external_ref

        # Add timestamps as ISO format strings
        fm["created"] = self.created.isoformat()
        fm["updated"] = self.updated.isoformat()

        return fm

    def to_markdown(self) -> str:
        """Convert full ticket to markdown string with frontmatter."""
        # Build the content sections
        content_parts = []

        if self.description:
            content_parts.append("## Description\n")
            content_parts.append(f"{self.description}\n")

        if self.design:
            content_parts.append("## Design\n")
            content_parts.append(f"{self.design}\n")

        if self.acceptance_criteria:
            content_parts.append("## Acceptance Criteria\n")
            content_parts.append(f"{self.acceptance_criteria}\n")

        if self.notes:
            content_parts.append("## Notes\n")
            for note in self.notes:
                content_parts.append(f"- {note}\n")

        content = "\n".join(content_parts).strip()

        # Create frontmatter post
        post = frontmatter.Post(content, **self.to_frontmatter())

        # Convert to string with frontmatter
        return frontmatter.dumps(post)

    @classmethod
    def from_dict(cls, data: dict) -> "Ticket":
        """Create Ticket from parsed frontmatter + content dict."""
        # Extract frontmatter fields
        ticket_data = {
            "id": data.get("id", ""),
            "title": data.get("title", ""),
            "type": TicketType(data.get("type", "task")),
            "status": TicketStatus(data.get("status", "open")),
            "priority": data.get("priority", 2),
            "assignee": data.get("assignee"),
            "tags": data.get("tags", []),
            "deps": data.get("deps", []),
            "links": data.get("links", []),
            "parent": data.get("parent"),
            "external_ref": data.get("external_ref"),
        }

        # Parse timestamps
        if "created" in data:
            if isinstance(data["created"], str):
                ticket_data["created"] = datetime.fromisoformat(data["created"])
            else:
                ticket_data["created"] = data["created"]

        if "updated" in data:
            if isinstance(data["updated"], str):
                ticket_data["updated"] = datetime.fromisoformat(data["updated"])
            else:
                ticket_data["updated"] = data["updated"]

        # Extract content sections from the content string
        content = data.get("content", "")
        if content:
            # Parse content sections
            sections = {}
            current_section = None
            current_content = []

            for line in content.split("\n"):
                if line.startswith("## "):
                    # Save previous section
                    if current_section:
                        sections[current_section] = "\n".join(current_content).strip()
                    # Start new section
                    current_section = line[3:].strip().lower().replace(" ", "_")
                    current_content = []
                elif current_section:
                    current_content.append(line)

            # Save last section
            if current_section:
                sections[current_section] = "\n".join(current_content).strip()

            # Map sections to ticket fields
            ticket_data["description"] = sections.get("description")
            ticket_data["design"] = sections.get("design")
            ticket_data["acceptance_criteria"] = sections.get("acceptance_criteria")

            # Parse notes if present
            if "notes" in sections:
                notes_text = sections["notes"]
                notes = []
                for line in notes_text.split("\n"):
                    line = line.strip()
                    if line.startswith("- "):
                        notes.append(line[2:])
                ticket_data["notes"] = notes

        return cls(**ticket_data)

    def is_blocked(self) -> bool:
        """Check if ticket has unresolved dependencies."""
        # Note: This is a placeholder - actual check requires storage access
        return len(self.deps) > 0

    def add_note(self, text: str) -> None:
        """Add a timestamped note."""
        timestamp = now_utc().strftime("%Y-%m-%d %H:%M")
        self.notes.append(f"{timestamp}: {text}")
        self.updated = now_utc()
