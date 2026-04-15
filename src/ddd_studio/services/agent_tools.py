"""Agent tool functions for domain model manipulation.

Tools are decorated with @tool and bound to the LLM via bind_tools.
The ModelAccessor is injected via closure in create_tools().
"""

from __future__ import annotations

import json
import re
from typing import Literal

from domain.models.tool_schemas import ToolResult
from langchain_core.tools import tool
from models.domain_analysis import AristaGrafo, NodoGrafo
from services.model_accessor import ModelAccessor

# Map ElementType prefixes for semantic ID generation
_TYPE_PREFIX = {
    "Actor": "act",
    "Sistema Externo": "svc",
    "Hotspot": "hot",
    "Comando": "cmd",
    "Evento": "evt",
    "Política": "pol",
    "Entidad Raíz": "ent",
    "Agregado": "agg",
    "Read Model": "rm",
    "Vista": "vis",
    "Proyección": "proy",
    "Regla de Negocio": "rule",
    "Política de UI": "uipol",
}


def _generate_id(node_type: str, node_name: str) -> str:
    """Generate a semantic ID: {type_prefix}_{snake_case_name}."""
    prefix = _TYPE_PREFIX.get(node_type, "node")
    # Convert to snake_case
    name = node_name.strip()
    name = re.sub(r"[^\w\s]", "", name)
    name = re.sub(r"\s+", "_", name).lower()
    return f"{prefix}_{name}"


def _get_container(accessor: ModelAccessor, scope: str, aggregate_name: str | None):
    """Return (container_with_nodos_and_aristas, error_ToolResult_json_or_None)."""
    model = accessor.get_model()
    if scope == "big_picture":
        return model.big_picture, None
    elif scope == "aggregate":
        if not aggregate_name:
            return None, ToolResult(
                success=False,
                message="aggregate_name is required for scope 'aggregate'",
            ).model_dump_json()
        agg = accessor.find_aggregate(aggregate_name)
        if not agg:
            return None, ToolResult(
                success=False,
                message=f"Aggregate '{aggregate_name}' not found. Available: {[a.nombre_agregado for a in model.agregados]}",
            ).model_dump_json()
        return agg, None
    else:
        return None, ToolResult(success=False, message=f"Unknown scope: {scope}").model_dump_json()


def _find_node_in_container(container, name: str) -> NodoGrafo | None:
    """Find a node by name in a container with .nodos."""
    for n in container.nodos:
        if n.nombre == name:
            return n
    return None


def _resolve_node_id(container, name: str) -> str | None:
    """Resolve a node name to its ID within a container."""
    node = _find_node_in_container(container, name)
    return node.id if node else None


def create_tools(accessor: ModelAccessor) -> list:
    """Create tool functions with ModelAccessor captured in closure."""

    @tool
    def query_model(
        section: Literal["big_picture", "aggregate", "read_models", "policies", "summary"],
        aggregate_name: str | None = None,
    ) -> str:
        """Query the current domain model. Use 'aggregate' with aggregate_name to get a specific aggregate."""
        model = accessor.get_model()

        if section == "big_picture":
            data = model.big_picture.model_dump()
        elif section == "aggregate":
            if not aggregate_name:
                return ToolResult(
                    success=False,
                    message="aggregate_name is required when section is 'aggregate'",
                ).model_dump_json()
            agg = accessor.find_aggregate(aggregate_name)
            if not agg:
                return ToolResult(
                    success=False,
                    message=f"Aggregate '{aggregate_name}' not found. Available: {[a.nombre_agregado for a in model.agregados]}",
                ).model_dump_json()
            data = agg.model_dump()
        elif section == "read_models":
            data = [rm.model_dump() for rm in model.read_models]
        elif section == "policies":
            data = [p.model_dump() for p in model.politicas_inter_agregados]
        elif section == "summary":
            data = {
                "nombre_proyecto": model.nombre_proyecto,
                "big_picture_nodes": len(model.big_picture.nodos),
                "big_picture_edges": len(model.big_picture.aristas),
                "aggregates": [
                    {
                        "name": a.nombre_agregado,
                        "nodes": len(a.nodos),
                        "edges": len(a.aristas),
                    }
                    for a in model.agregados
                ],
                "read_models": len(model.read_models),
                "inter_aggregate_policies": len(model.politicas_inter_agregados),
            }
        else:
            return ToolResult(success=False, message=f"Unknown section: {section}").model_dump_json()

        return json.dumps(data, ensure_ascii=False)

    @tool
    def add_node(
        scope: Literal["big_picture", "aggregate"],
        node_name: str,
        node_type: str,
        description: str,
        aggregate_name: str | None = None,
        nivel: Literal["big_picture", "process_level", "read_model"] = "big_picture",
    ) -> str:
        """Add a new node to the domain model."""
        container, err = _get_container(accessor, scope, aggregate_name)
        if err:
            return err

        # Default nivel based on scope
        effective_nivel = "process_level" if scope == "aggregate" else nivel

        node_id = _generate_id(node_type, node_name)

        # Check for duplicate by ID or by name+type
        if any(n.id == node_id for n in container.nodos) or any(
            n.nombre == node_name and n.tipo_elemento == node_type for n in container.nodos
        ):
            return ToolResult(
                success=False,
                message=f"Node '{node_name}' of type '{node_type}' already exists in {scope}.",
                affected_elements=[],
            ).model_dump_json()

        accessor.snapshot("add_node", f"Add {node_type} '{node_name}'")

        new_node = NodoGrafo(
            id=node_id,
            tipo_elemento=node_type,
            nombre=node_name,
            descripcion=description,
            nivel=effective_nivel,
        )
        container.nodos.append(new_node)

        return ToolResult(
            success=True,
            message=f"Added {node_type} '{node_name}' (id: {node_id}) to {scope}"
            + (f" aggregate '{aggregate_name}'" if aggregate_name else ""),
            affected_elements=[node_id],
        ).model_dump_json()

    @tool
    def add_edge(
        scope: Literal["big_picture", "aggregate", "inter_aggregate"],
        source_name: str,
        target_name: str,
        description: str,
        aggregate_name: str | None = None,
    ) -> str:
        """Add an edge between two nodes. Both nodes must exist in the scope."""
        model = accessor.get_model()

        if scope == "inter_aggregate":
            # For inter-aggregate, search across all nodes
            all_nodes = list(model.big_picture.nodos)
            for agg in model.agregados:
                all_nodes.extend(agg.nodos)
            source_id = next((n.id for n in all_nodes if n.nombre == source_name), None)
            target_id = next((n.id for n in all_nodes if n.nombre == target_name), None)
            if not source_id:
                return ToolResult(
                    success=False,
                    message=f"Source node '{source_name}' not found in any scope.",
                ).model_dump_json()
            if not target_id:
                return ToolResult(
                    success=False,
                    message=f"Target node '{target_name}' not found in any scope.",
                ).model_dump_json()

            accessor.snapshot("add_edge", f"Add inter-aggregate edge {source_name} -> {target_name}")
            model.politicas_inter_agregados.append(
                AristaGrafo(fuente=source_id, destino=target_id, descripcion=description)
            )
            return ToolResult(
                success=True,
                message=f"Added inter-aggregate edge from '{source_name}' to '{target_name}'",
                affected_elements=[source_id, target_id],
            ).model_dump_json()

        container, err = _get_container(accessor, scope, aggregate_name)
        if err:
            return err

        source_id = _resolve_node_id(container, source_name)
        target_id = _resolve_node_id(container, target_name)

        if not source_id:
            return ToolResult(
                success=False,
                message=f"Source node '{source_name}' not found in {scope}.",
            ).model_dump_json()
        if not target_id:
            return ToolResult(
                success=False,
                message=f"Target node '{target_name}' not found in {scope}.",
            ).model_dump_json()

        accessor.snapshot("add_edge", f"Add edge {source_name} -> {target_name}")
        container.aristas.append(AristaGrafo(fuente=source_id, destino=target_id, descripcion=description))
        return ToolResult(
            success=True,
            message=f"Added edge from '{source_name}' to '{target_name}' in {scope}",
            affected_elements=[source_id, target_id],
        ).model_dump_json()

    @tool
    def rename_element(
        element_type: Literal["node", "aggregate"],
        current_name: str,
        new_name: str,
        scope: Literal["big_picture", "aggregate"] | None = None,
        aggregate_name: str | None = None,
    ) -> str:
        """Rename a node or aggregate in the domain model."""
        model = accessor.get_model()

        if element_type == "aggregate":
            agg = accessor.find_aggregate(current_name)
            if not agg:
                return ToolResult(
                    success=False,
                    message=f"Aggregate '{current_name}' not found.",
                ).model_dump_json()
            accessor.snapshot("rename_element", f"Rename aggregate '{current_name}' to '{new_name}'")
            agg.nombre_agregado = new_name
            return ToolResult(
                success=True,
                message=f"Renamed aggregate '{current_name}' to '{new_name}'",
                affected_elements=[new_name],
            ).model_dump_json()

        # element_type == "node"
        # Determine search scope
        containers = []
        if scope == "big_picture" or scope is None:
            containers.append(("big_picture", model.big_picture))
        if scope == "aggregate" or scope is None:
            for agg in model.agregados:
                if aggregate_name is None or agg.nombre_agregado == aggregate_name:
                    containers.append(("aggregate", agg))

        target_node = None
        target_container = None
        for label, container in containers:
            node = _find_node_in_container(container, current_name)
            if node:
                target_node = node
                target_container = container
                break

        if not target_node:
            return ToolResult(
                success=False,
                message=f"Node '{current_name}' not found in {scope or 'any scope'}.",
            ).model_dump_json()

        accessor.snapshot("rename_element", f"Rename node '{current_name}' to '{new_name}'")

        old_id = target_node.id
        new_id = _generate_id(target_node.tipo_elemento, new_name)

        target_node.nombre = new_name
        target_node.id = new_id

        # Update edge references in the same container
        for edge in target_container.aristas:
            if edge.fuente == old_id:
                edge.fuente = new_id
            if edge.destino == old_id:
                edge.destino = new_id

        # Also update inter-aggregate policies
        for edge in model.politicas_inter_agregados:
            if edge.fuente == old_id:
                edge.fuente = new_id
            if edge.destino == old_id:
                edge.destino = new_id

        return ToolResult(
            success=True,
            message=f"Renamed node '{current_name}' to '{new_name}' (id: {old_id} -> {new_id})",
            affected_elements=[new_id],
        ).model_dump_json()

    @tool
    def delete_node(
        scope: Literal["big_picture", "aggregate"],
        node_name: str,
        aggregate_name: str | None = None,
    ) -> str:
        """Delete a node and its connected edges from the domain model."""
        container, err = _get_container(accessor, scope, aggregate_name)
        if err:
            return err

        node = _find_node_in_container(container, node_name)
        if not node:
            return ToolResult(
                success=False,
                message=f"Node '{node_name}' not found in {scope}.",
            ).model_dump_json()

        accessor.snapshot("delete_node", f"Delete node '{node_name}'")

        node_id = node.id
        container.nodos = [n for n in container.nodos if n.id != node_id]

        # Cascade delete edges referencing this node
        original_edges = len(container.aristas)
        container.aristas = [e for e in container.aristas if e.fuente != node_id and e.destino != node_id]
        removed_edges = original_edges - len(container.aristas)

        # Also clean up inter-aggregate policies
        model = accessor.get_model()
        model.politicas_inter_agregados = [
            e for e in model.politicas_inter_agregados if e.fuente != node_id and e.destino != node_id
        ]

        return ToolResult(
            success=True,
            message=f"Deleted node '{node_name}' and {removed_edges} connected edge(s) from {scope}",
            affected_elements=[node_id],
        ).model_dump_json()

    @tool
    def delete_edge(
        scope: Literal["big_picture", "aggregate", "inter_aggregate"],
        source_name: str,
        target_name: str,
        aggregate_name: str | None = None,
    ) -> str:
        """Delete an edge between two nodes."""
        model = accessor.get_model()

        if scope == "inter_aggregate":
            # Search all nodes for IDs
            all_nodes = list(model.big_picture.nodos)
            for agg in model.agregados:
                all_nodes.extend(agg.nodos)
            source_id = next((n.id for n in all_nodes if n.nombre == source_name), None)
            target_id = next((n.id for n in all_nodes if n.nombre == target_name), None)
            if not source_id or not target_id:
                return ToolResult(
                    success=False,
                    message=f"Could not resolve nodes '{source_name}' and/or '{target_name}'.",
                ).model_dump_json()
            original = len(model.politicas_inter_agregados)
            model.politicas_inter_agregados = [
                e for e in model.politicas_inter_agregados if not (e.fuente == source_id and e.destino == target_id)
            ]
            if len(model.politicas_inter_agregados) == original:
                return ToolResult(
                    success=False,
                    message=f"No inter-aggregate edge found from '{source_name}' to '{target_name}'.",
                ).model_dump_json()
            accessor.snapshot("delete_edge", f"Delete inter-aggregate edge {source_name} -> {target_name}")
            return ToolResult(
                success=True,
                message=f"Deleted inter-aggregate edge from '{source_name}' to '{target_name}'",
                affected_elements=[source_id, target_id],
            ).model_dump_json()

        container, err = _get_container(accessor, scope, aggregate_name)
        if err:
            return err

        source_id = _resolve_node_id(container, source_name)
        target_id = _resolve_node_id(container, target_name)

        if not source_id or not target_id:
            return ToolResult(
                success=False,
                message=f"Could not resolve nodes '{source_name}' and/or '{target_name}' in {scope}.",
            ).model_dump_json()

        original = len(container.aristas)
        container.aristas = [e for e in container.aristas if not (e.fuente == source_id and e.destino == target_id)]
        if len(container.aristas) == original:
            return ToolResult(
                success=False,
                message=f"No edge found from '{source_name}' to '{target_name}' in {scope}.",
            ).model_dump_json()

        accessor.snapshot("delete_edge", f"Delete edge {source_name} -> {target_name}")
        return ToolResult(
            success=True,
            message=f"Deleted edge from '{source_name}' to '{target_name}' in {scope}",
            affected_elements=[source_id, target_id],
        ).model_dump_json()

    @tool
    def undo_last_change() -> str:
        """Undo the last write operation on the domain model."""
        record = accessor.undo()
        if not record:
            return ToolResult(
                success=False,
                message="No previous changes to revert.",
            ).model_dump_json()

        return ToolResult(
            success=True,
            message=f"Undone '{record.tool_name}': {record.description}",
            affected_elements=[],
        ).model_dump_json()

    return [
        query_model,
        add_node,
        add_edge,
        rename_element,
        delete_node,
        delete_edge,
        undo_last_change,
    ]
