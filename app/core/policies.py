PROJECT_TRANSITIONS = {
    "planning": {"active", "archived"},
    "active": {"on_hold", "completed", "archived"},
    "on_hold": {"active", "archived"},
    "completed": {"archived"},
    "archived": set(),
}
TASK_TRANSITIONS = {
    "backlog": {"todo", "cancelled"},
    "todo": {"backlog", "in_progress", "cancelled"},
    "in_progress": {"todo", "blocked", "review", "cancelled"},
    "blocked": {"in_progress", "cancelled"},
    "review": {"in_progress", "done"},
    "done": set(),
    "cancelled": {"todo"},
}
MANAGER_ROLES = {"organization_admin", "project_manager"}
