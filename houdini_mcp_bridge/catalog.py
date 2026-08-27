"""SideFX-documented tool catalog for HoudiniMCP."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional, Literal

from pydantic import Field

from .sidefx_docs import official_url
from .registry import DocRef, ToolArguments, ToolRegistry, ToolSpec


Relay = Callable[[str, Dict[str, Any]], Dict[str, Any]]


def hom(entry: str, symbol: str) -> DocRef:
    return DocRef(
        kind="hom", archive="hom.zip", entry=entry, symbol=symbol,
        official_url=official_url("hom.zip", entry),
    )


def node_doc(category: str, node_type: str) -> DocRef:
    entry = f"{category}/{node_type}.txt"
    return DocRef(
        kind="node", archive="nodes.zip", entry=entry,
        symbol=f"{category}/{node_type}", official_url=official_url("nodes.zip", entry),
    )


class NoArgs(ToolArguments):
    pass


class CreateNodeArgs(ToolArguments):
    node_type: str
    parent_path: str = "/obj"
    name: Optional[str] = None
    position: Optional[List[float]] = None
    parameters: Optional[Dict[str, Any]] = None


class CodeArgs(ToolArguments):
    code: str


class NodePathArgs(ToolArguments):
    path: str


class ConnectArgs(ToolArguments):
    from_path: str
    to_path: str
    input_index: int = Field(default=0, ge=0)
    output_index: int = Field(default=0, ge=0)


class DisconnectArgs(ToolArguments):
    path: str
    input_index: int = Field(default=0, ge=0)


class SetParametersArgs(ToolArguments):
    path: str
    parameters: Dict[str, Any]
    overwrite_channel: bool = False


class SearchNodeTypesArgs(ToolArguments):
    parent_path: str = "/obj"
    query: str = ""
    category: Optional[str] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class NodeTypeSchemaArgs(ToolArguments):
    parent_path: str
    node_type: str
    pattern: Optional[str] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class NetworkSnapshotArgs(ToolArguments):
    path: str
    depth: int = Field(default=1, ge=0, le=5)
    include_parameters: bool = False
    max_nodes: int = Field(default=200, ge=1, le=2000)
    max_parameters: int = Field(default=20, ge=0, le=100)
    max_bytes: int = Field(default=262144, ge=4096, le=2097152)


class HdaCandidateArgs(ToolArguments):
    path: str
    library_path: Optional[str] = None
    type_name: Optional[str] = None


class SearchHdaArgs(ToolArguments):
    query: str = ""
    parent_path: Optional[str] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class HdaInfoArgs(ToolArguments):
    path: Optional[str] = None
    definition_id: Optional[str] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=200)


class HdaPromotion(ToolArguments):
    source_node: str
    source_parameter: str
    name: str
    label: Optional[str] = None
    folder: Optional[str] = None


class CreateHdaArgs(ToolArguments):
    path: str
    type_name: str
    label: str
    library_path: str
    description: Optional[str] = None
    promotions: List[HdaPromotion] = Field(default_factory=list, max_length=100)
    dry_run: bool = True
    plan_id: Optional[str] = None
    expected_revision: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=128)
    overwrite: Literal[False] = False


class ValidateHdaArgs(ToolArguments):
    path: Optional[str] = None
    definition_id: Optional[str] = None


class HdaInterfacePatchArgs(ToolArguments):
    path: str
    promotions: List[HdaPromotion] = Field(min_length=1, max_length=100)
    dry_run: bool = True
    plan_id: Optional[str] = None
    expected_revision: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=128)


class GraphOperation(ToolArguments):
    op: Literal["create", "delete", "connect", "disconnect", "set_parameters", "set_flags", "rename", "set_position"]
    id: Optional[str] = None
    path: Optional[str] = None
    parent_path: Optional[str] = None
    node_type: Optional[str] = None
    name: Optional[str] = None
    from_path: Optional[str] = None
    to_path: Optional[str] = None
    input_index: int = Field(default=0, ge=0)
    output_index: int = Field(default=0, ge=0)
    parameters: Optional[Dict[str, Any]] = None
    flags: Optional[Dict[str, bool]] = None
    position: Optional[List[float]] = None
    overwrite_channel: bool = False


class GraphPatchArgs(ToolArguments):
    operations: List[GraphOperation] = Field(min_length=1, max_length=100)
    dry_run: bool = True
    atomic: bool = True
    expected_revision: Optional[str] = None
    idempotency_key: Optional[str] = Field(default=None, min_length=1, max_length=128)


class ParameterSchemaArgs(ToolArguments):
    path: str
    pattern: Optional[str] = None
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=50, ge=1, le=500)


class NodeFlagsArgs(ToolArguments):
    path: str
    display: Optional[bool] = None
    render: Optional[bool] = None
    bypass: Optional[bool] = None
    template: Optional[bool] = None


class FindErrorsArgs(ToolArguments):
    root_path: str = "/obj"
    include_warnings: bool = False


class CreateWrangleArgs(ToolArguments):
    parent_path: str
    vex_code: str
    name: Optional[str] = None
    run_over: str = "points"
    input_node: Optional[str] = None


class SetWrangleArgs(ToolArguments):
    path: str
    vex_code: str
    validate_result: bool = Field(default=True, alias="validate")


class GeometryDataArgs(ToolArguments):
    path: str
    element: str = "points"
    attributes: Optional[List[str]] = None
    start: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)


class RenderSingleArgs(ToolArguments):
    orthographic: bool = False
    rotation: List[float] = Field(default_factory=lambda: [0, 90, 0])
    render_path: str = "C:/temp/"
    render_engine: str = "opengl"
    karma_engine: str = "cpu"


class RenderQuadArgs(ToolArguments):
    orthographic: bool = True
    render_path: str = "C:/temp/"
    render_engine: str = "opengl"
    karma_engine: str = "cpu"


class RenderCameraArgs(ToolArguments):
    camera_path: str
    render_path: str = "C:/temp/"
    render_engine: str = "opengl"
    karma_engine: str = "cpu"


class OpusStructureArgs(ToolArguments):
    structure: str


class OpusCreateArgs(ToolArguments):
    structure: str
    parameters: Dict[str, Any]
    count: int = Field(default=1, ge=1)


class OpusVariateArgs(ToolArguments):
    result_id: str
    count: int = Field(default=12, ge=1)


class OpusJobArgs(ToolArguments):
    batch_id: str


class OpusImportArgs(ToolArguments):
    download_url: str
    node_name: Optional[str] = None


class ModifyNodeArgs(ToolArguments):
    path: str
    parameters: Optional[Dict[str, Any]] = None
    position: Optional[List[float]] = None
    name: Optional[str] = None


class SetMaterialArgs(ToolArguments):
    node_path: str
    material_type: Optional[str] = None
    name: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class MaterialAssignmentsArgs(ToolArguments):
    path: str = "/obj"
    recursive: bool = True
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)
    max_assignments: int = Field(default=10000, ge=1, le=100000)


class StageSnapshotArgs(ToolArguments):
    path: str
    prim_path: str = "/"
    depth: int = Field(default=2, ge=0, le=10)
    include_materials: bool = True
    max_prims: int = Field(default=500, ge=1, le=5000)
    max_bytes: int = Field(default=524288, ge=4096, le=4194304)


class FindNodesArgs(ToolArguments):
    root_path: str = "/obj"
    name_pattern: Optional[str] = None
    type_pattern: Optional[str] = None
    recursive: bool = True
    offset: int = Field(default=0, ge=0)
    limit: int = Field(default=100, ge=1, le=500)


class SaveHipArgs(ToolArguments):
    path: Optional[str] = None
    overwrite: bool = False


def build_registry(
    relay: Relay,
    local_handlers: Optional[Dict[str, Callable[[Dict[str, Any]], Any]]] = None,
    opus_availability: Optional[Callable[[], tuple[bool, Optional[str]]]] = None,
    houdini_availability: Optional[Callable[[], tuple[Optional[bool], Optional[str]]]] = None,
) -> ToolRegistry:
    registry = ToolRegistry()
    local_handlers = local_handlers or {}

    def remote(command: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        return lambda args: relay(command, args)

    def local(name: str) -> Callable[[Dict[str, Any]], Dict[str, Any]]:
        def invoke(args: Dict[str, Any]) -> Dict[str, Any]:
            handler = local_handlers.get(name)
            if not handler:
                return {"status": "error", "message": f"Local handler unavailable: {name}", "origin": "catalog"}
            result = handler(args)
            if isinstance(result, dict) and result.get("status") in {"success", "error"}:
                return result
            return {"status": "success", "result": result}
        return invoke

    specs = [
        ToolSpec("get_scene_info", "scene", "Inspect the current Houdini scene and top-level networks.", NoArgs, remote("get_scene_info"), [hom("hou/hipFile.txt", "hou.hipFile"), hom("hou/Node.txt", "hou.Node")], ("scene", "networks", "objects")),
        ToolSpec("create_node", "node", "Create a node under a compatible Houdini network.", CreateNodeArgs, remote("create_node"), [hom("hou/OpNode.txt", "hou.OpNode.createNode")], ("create", "node", "sop", "obj"), True, True, "medium"),
        ToolSpec("execute_houdini_code", "advanced", "Execute arbitrary Python in Houdini as a last resort.", CodeArgs, remote("execute_code"), [hom("hou/ScriptEvalContext.txt", "Houdini Python")], ("python", "hou", "raw", "fallback"), True, False, "high", effect_scope="scene", rollback_strategy="none", prerequisites=("connected Houdini session",)),
        ToolSpec("connect_nodes", "graph", "Connect an output to an input in the same Houdini network.", ConnectArgs, remote("connect_nodes"), [hom("hou/OpNode.txt", "hou.OpNode.setInput")], ("wire", "connect", "input", "output"), True, True, "medium"),
        ToolSpec("disconnect_node_input", "graph", "Disconnect one node input.", DisconnectArgs, remote("disconnect_input"), [hom("hou/OpNode.txt", "hou.OpNode.setInput")], ("disconnect", "wire"), True, True, "medium"),
        ToolSpec("delete_node", "node", "Delete a node by path.", NodePathArgs, remote("delete_node"), [hom("hou/OpNode.txt", "hou.OpNode.destroy")], ("delete", "remove"), True, True, "medium"),
        ToolSpec("set_parameters", "parameter", "Set validated scalar, tuple, or menu parameters in one undo group.", SetParametersArgs, remote("set_parameters"), [hom("hou/Parm.txt", "hou.Parm.set"), hom("hou/ParmTuple.txt", "hou.ParmTuple.set")], ("parameter", "parm", "menu", "value"), True, True, "medium"),
        ToolSpec("search_node_types", "discovery", "Search node types that are live and creatable in a parent network.", SearchNodeTypesArgs, remote("search_node_types"), [hom("hou/NodeTypeCategory.txt", "hou.NodeTypeCategory.nodeTypes")], ("node", "type", "discover", "category")),
        ToolSpec("get_node_type_schema", "discovery", "Inspect a live node type's inputs, outputs and parameter templates.", NodeTypeSchemaArgs, remote("get_node_type_schema"), [hom("hou/NodeType.txt", "hou.NodeType"), hom("hou/ParmTemplate.txt", "hou.ParmTemplate")], ("node", "type", "schema", "parameters")),
        ToolSpec("get_network_snapshot", "discovery", "Read a bounded, revisioned snapshot of a Houdini network.", NetworkSnapshotArgs, remote("get_network_snapshot"), [hom("hou/OpNode.txt", "hou.OpNode")], ("network", "snapshot", "revision", "connections"), result_size="bounded_large"),
        ToolSpec("get_parameter_schema", "parameter", "Discover live parameter names, types, ranges, defaults and menus.", ParameterSchemaArgs, remote("get_parameter_schema"), [hom("hou/ParmTemplate.txt", "hou.ParmTemplate")], ("parameter", "schema", "discover", "menu")),
        ToolSpec("set_node_flags", "node", "Set display, render, bypass, and template flags.", NodeFlagsArgs, remote("set_node_flags"), [hom("hou/OpNode.txt", "hou.OpNode flags")], ("display", "render", "bypass", "template"), True, True, "medium"),
        ToolSpec("layout_network", "graph", "Auto-layout the children of a network.", NodePathArgs, remote("layout_children"), [hom("hou/OpNode.txt", "hou.OpNode.layoutChildren")], ("layout", "network", "tidy"), True, True, "low"),
        ToolSpec("find_error_nodes", "validation", "Find nodes with cook errors or warnings.", FindErrorsArgs, remote("find_error_nodes"), [hom("hou/OpNode.txt", "hou.OpNode.errors")], ("errors", "warnings", "diagnose")),
        ToolSpec("cook_node", "validation", "Force-cook a node and return errors, warnings and timing.", NodePathArgs, remote("cook_node"), [hom("hou/OpNode.txt", "hou.OpNode.cook")], ("cook", "validate", "errors")),
        ToolSpec("create_wrangle", "vex", "Create, wire and validate an Attribute Wrangle SOP.", CreateWrangleArgs, remote("create_wrangle"), [node_doc("sop", "attribwrangle")], ("vex", "wrangle", "code"), True, True, "medium"),
        ToolSpec("set_wrangle_code", "vex", "Replace and optionally compile-check VEX on a wrangle.", SetWrangleArgs, remote("set_wrangle_code"), [node_doc("sop", "attribwrangle")], ("vex", "wrangle", "compile"), True, True, "medium"),
        ToolSpec("get_geometry_info", "geometry", "Summarize counts, bounds, attributes and groups.", NodePathArgs, remote("get_geometry_info"), [hom("hou/Geometry.txt", "hou.Geometry")], ("geometry", "attributes", "bounding box", "counts")),
        ToolSpec("get_geometry_data", "geometry", "Read paginated point or primitive attribute values.", GeometryDataArgs, remote("get_geometry_data"), [hom("hou/Geometry.txt", "hou.Geometry")], ("points", "primitives", "attributes", "data"), result_size="bounded_large"),
        ToolSpec("render_single_view", "render", "Render one generated view.", RenderSingleArgs, remote("render_single_view"), [hom("hou/GeometryViewport.txt", "hou.GeometryViewport")], ("render", "viewport", "image"), True, True, "medium", effect_scope="disk", rollback_strategy="none", prerequisites=("Houdini UI session",)),
        ToolSpec("render_quad_views", "render", "Render four orthographic or perspective views.", RenderQuadArgs, remote("render_quad_view"), [hom("hou/GeometryViewport.txt", "hou.GeometryViewport")], ("render", "quad", "views"), True, True, "medium", effect_scope="disk", rollback_strategy="none", prerequisites=("Houdini UI session",)),
        ToolSpec("render_specific_camera", "render", "Render from an existing camera node.", RenderCameraArgs, remote("render_specific_camera"), [hom("hou/ObjNode.txt", "hou.ObjNode")], ("render", "camera", "image"), True, True, "medium", effect_scope="disk", rollback_strategy="none", prerequisites=("Houdini UI session",)),
        ToolSpec("get_node_info", "node", "Inspect node type, position, flags, parameters and connections.", NodePathArgs, remote("get_node_info"), [hom("hou/OpNode.txt", "hou.OpNode")], ("node", "inspect", "connections")),
        ToolSpec("modify_node", "node", "Rename, move, or update an existing node.", ModifyNodeArgs, remote("modify_node"), [hom("hou/OpNode.txt", "hou.OpNode")], ("rename", "position", "modify"), True, True, "medium"),
        ToolSpec("set_material", "material", "Create or reuse a material and assign it to an OBJ node.", SetMaterialArgs, remote("set_material"), [node_doc("shop", "principledshader"), hom("hou/OpNode.txt", "hou.OpNode.createNode")], ("material", "shader", "principled"), True, True, "medium"),
        ToolSpec("find_nodes", "node", "Find nodes by root, name glob and live node type.", FindNodesArgs, remote("find_nodes"), [hom("hou/OpNode.txt", "hou.OpNode.allSubChildren")], ("find", "search", "node", "type")),
        ToolSpec("get_hip_info", "scene_file", "Inspect the current HIP file path and unsaved state.", NoArgs, remote("get_hip_info"), [hom("hou/hipFile.txt", "hou.hipFile")], ("hip", "file", "unsaved")),
        ToolSpec("save_hip", "scene_file", "Save the current HIP file with overwrite protection.", SaveHipArgs, remote("save_hip"), [hom("hou/hipFile.txt", "hou.hipFile.save")], ("hip", "save", "file"), True, False, "medium", effect_scope="disk", rollback_strategy="none"),
        ToolSpec("analyze_hda_candidate", "hda", "Analyze a subnetwork before creating an HDA definition.", HdaCandidateArgs, remote("analyze_hda_candidate"), [hom("hou/OpNode.txt", "hou.OpNode.createDigitalAsset")], ("hda", "asset", "candidate", "subnetwork")),
        ToolSpec("search_hda_definitions", "hda", "Search installed HDA definitions with stable identities.", SearchHdaArgs, remote("search_hda_definitions"), [hom("hou/hda.txt", "hou.hda.loadedFiles")], ("hda", "definition", "library", "namespace")),
        ToolSpec("get_hda_info", "hda", "Inspect an HDA instance or definition, including interface and revision.", HdaInfoArgs, remote("get_hda_info"), [hom("hou/HDADefinition.txt", "hou.HDADefinition")], ("hda", "definition", "interface", "sections")),
        ToolSpec("create_hda_from_subnetwork", "hda", "Plan or transactionally create a new external HDA from a validated subnetwork.", CreateHdaArgs, remote("create_hda_from_subnetwork"), [hom("hou/OpNode.txt", "hou.OpNode.createDigitalAsset"), hom("hou/HDADefinition.txt", "hou.HDADefinition")], ("hda", "create", "promote", "library"), True, False, "high", effect_scope="disk", rollback_strategy="compensation", prerequisites=("writable external HDA directory",)),
        ToolSpec("apply_hda_interface_patch", "hda", "Plan or apply validated parameter promotions to an existing HDA interface.", HdaInterfacePatchArgs, remote("apply_hda_interface_patch"), [hom("hou/HDADefinition.txt", "hou.HDADefinition.setParmTemplateGroup"), hom("hou/ParmTemplateGroup.txt", "hou.ParmTemplateGroup")], ("hda", "interface", "parameter", "promote"), True, False, "high", effect_scope="disk", rollback_strategy="backup", prerequisites=("external writable HDA library",)),
        ToolSpec("validate_hda", "hda", "Validate an HDA definition and a controlled instance cook.", ValidateHdaArgs, remote("validate_hda"), [hom("hou/HDADefinition.txt", "hou.HDADefinition"), hom("hou/OpNode.txt", "hou.OpNode.cook")], ("hda", "validate", "cook", "hash")),
        ToolSpec("apply_graph_patch", "graph", "Validate and apply a bounded graph edit as one operation.", GraphPatchArgs, remote("apply_graph_patch"), [hom("hou/OpNode.txt", "hou.OpNode"), hom("hou/undos.txt", "hou.undos.group")], ("graph", "patch", "atomic", "batch"), True, True, "medium"),
        ToolSpec("get_material_assignments", "material", "Inspect OBJ, SOP, and USD material bindings without modifying the scene.", MaterialAssignmentsArgs, remote("get_material_assignments"), [hom("hou/Parm.txt", "hou.Parm.eval"), hom("hou/Geometry.txt", "hou.Geometry")], ("material", "assignment", "binding", "shop_materialpath")),
        ToolSpec("get_stage_snapshot", "usd", "Read a bounded, revisioned USD stage and layer snapshot from a LOP node.", StageSnapshotArgs, remote("get_stage_snapshot"), [hom("hou/LopNode.txt", "hou.LopNode.stage")], ("usd", "solaris", "stage", "prim", "layer"), prerequisites=("Solaris/LOP context",), result_size="bounded_large"),
    ]

    opus_specs = [
        ToolSpec("opus_get_model_names", "opus", "List OPUS procedural model names.", NoArgs, local("opus_get_model_names"), [hom("hou/OpNode.txt", "hou.OpNode")], ("opus", "assets", "models"), availability=opus_availability),
        ToolSpec("opus_get_model_params_schema", "opus", "Get the OPUS parameter schema for a structure.", OpusStructureArgs, local("opus_get_model_params_schema"), [hom("hou/ParmTemplate.txt", "hou.ParmTemplate")], ("opus", "schema", "parameters"), availability=opus_availability),
        ToolSpec("opus_create_model", "opus", "Submit an OPUS model generation job.", OpusCreateArgs, local("opus_create_model"), [hom("hou/OpNode.txt", "hou.OpNode")], ("opus", "create", "model"), True, False, "medium", availability=opus_availability),
        ToolSpec("opus_variate_model", "opus", "Submit OPUS model variations.", OpusVariateArgs, local("opus_variate_model"), [hom("hou/OpNode.txt", "hou.OpNode")], ("opus", "variation", "model"), True, False, "medium", availability=opus_availability),
        ToolSpec("opus_check_job_status", "opus", "Check an OPUS batch job.", OpusJobArgs, local("opus_check_job_status"), [hom("hou/OpNode.txt", "hou.OpNode")], ("opus", "job", "status"), availability=opus_availability),
        ToolSpec("opus_import_model_url", "opus", "Download and import an OPUS model archive.", OpusImportArgs, local("opus_import_model_url"), [hom("hou/hipFile.txt", "hou.hipFile")], ("opus", "import", "download"), True, True, "high", availability=opus_availability),
    ]

    if houdini_availability is not None:
        for spec in specs:
            spec.availability = houdini_availability
    for spec in specs + opus_specs:
        registry.register(spec)
    return registry
