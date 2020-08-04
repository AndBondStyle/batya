"""
Pydantic's BaseModel patch roadmap:
[ ] 1. Don't allow mutation, but allow dynamically setting/creating private fields
[ ] 2. Do not trigger on `@async_property` and `field: Awaitable[...]`
[ ] 3. Pretty tree-like formatting (max line width = 80) + extra formatting options?
"""
