# TOON Format (Token-Oriented Object Notation)

**TOON** is a custom, optimized data representation format designed specifically for Large Language Models (LLMs). It serves as a context injection format for the Studio's AI Assistant.

## Why TOON?
Standard JSON is verbose. It uses many tokens for syntax (`"`, `:`, `,`, `{`, `}`) that carry no semantic value. 
TOON reduces token usage by **30-40%** compared to JSON by using:
1. **Significant Indentation** (like YAML) for hierarchy.
2. **Tabular Data** (Pipe-separated) for arrays of uniform objects.
3. **Minimal Delimiters** (removing quotes and braces).

## Syntax Guide

### 1. Hierarchy
Indentation defines scope.
```yaml
ROOT:
  aggregates:
    - name: PaymentModule
```

### 2. Tabular Nodes
Arrays of objects are represented as tables. The header defines the schema once.
```text
    nodes: [Type | Name | Description]
    | Command | Pay | Process payment
    | Event   | Paid | Payment completed
```

### 3. Directional Flows
Relationships are represented with an arrow syntax, making them intuitive for the LLM to follow as a "path".
```text
    flows: [Description | Source -> Target]
    | Triggers | Pay -> Paid
```

## Example (Before vs After)

**JSON (Verbose):**
```json
{
  "nodes": [
    { "type": "Command", "name": "Pay", "desc": "Process payment" },
    { "type": "Event", "name": "Paid", "desc": "Payment completed" }
  ]
}
```

**TOON (Optimized):**
```text
nodes: [Type | Name | Desc]
| Command | Pay | Process payment
| Event | Paid | Payment completed
```

## Integration
The TOON generator is implemented in `src/ui/components/chat.py` via the `get_optimized_domain_context` function. It dynamically converts the Pydantic `DomainAnalysis` model into this string format before feeding it to **Google Gemini** to ensure high-density context and superior architectural reasoning.
