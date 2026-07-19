"""SideFX-documented tool catalog for HoudiniMCP."""

from __future__ import annotations

from typing import Any, Callable, Dict, List, Optional

from pydantic import Field

from sidefx_docs import official_url
from tool_registry import DocRef, ToolArguments, ToolRegistry, ToolSpec


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
        ToolSpec("execute_houdini_code", "advanced", "Execute arbitrary Python in Houdini as a last resort.", CodeArgs, remote("execute_code"), [hom("hou/ScriptEvalContext.txt", "Houdini Python")], ("python", "hou", "raw", "fallback"), True, False, "high"),
        ToolSpec("connect_nodes", "graph", "Connect an output to an input in the same Houdini network.", ConnectArgs, remote("connect_nodes"), [hom("hou/OpNode.txt", "hou.OpNode.setInput")], ("wire", "connect", "input", "output"), True, True, "medium"),
        ToolSpec("disconnect_node_input", "graph", "Disconnect one node input.", DisconnectArgs, remote("disconnect_input"), [hom("hou/OpNode.txt", "hou.OpNode.setInput")], ("disconnect", "wire"), True, True, "medium"),
        ToolSpec("delete_node", "node", "Delete a node by path.", NodePathArgs, remote("delete_node"), [hom("hou/OpNode.txt", "hou.OpNode.destroy")], ("delete", "remove"), True, True, "medium"),
        ToolSpec("set_parameters", "parameter", "Set validated scalar, tuple, or menu parameters in one undo group.", SetParametersArgs, remote("set_parameters"), [hom("hou/Parm.txt", "hou.Parm.set"), hom("hou/ParmTuple.txt", "hou.ParmTuple.set")], ("parameter", "parm", "menu", "value"), True, True, "medium"),
        ToolSpec("get_parameter_schema", "parameter", "Discover live parameter names, types, ranges, defaults and menus.", ParameterSchemaArgs, remote("get_parameter_schema"), [hom("hou/ParmTemplate.txt", "hou.ParmTemplate")], ("parameter", "schema", "discover", "menu")),
        ToolSpec("set_node_flags", "node", "Set display, render, bypass, and template flags.", NodeFlagsArgs, remote("set_node_flags"), [hom("hou/OpNode.txt", "hou.OpNode flags")], ("display", "render", "bypass", "template"), True, True, "medium"),
        ToolSpec("layout_network", "graph", "Auto-layout the children of a network.", NodePathArgs, remote("layout_children"), [hom("hou/OpNode.txt", "hou.OpNode.layoutChildren")], ("layout", "network", "tidy"), True, True, "low"),
        ToolSpec("find_error_nodes", "validation", "Find nodes with cook errors or warnings.", FindErrorsArgs, remote("find_error_nodes"), [hom("hou/OpNode.txt", "hou.OpNode.errors")], ("errors", "warnings", "diagnose")),
        ToolSpec("cook_node", "validation", "Force-cook a node and return errors, warnings and timing.", NodePathArgs, remote("cook_node"), [hom("hou/OpNode.txt", "hou.OpNode.cook")], ("cook", "validate", "errors")),
        ToolSpec("create_wrangle", "vex", "Create, wire and validate an Attribute Wrangle SOP.", CreateWrangleArgs, remote("create_wrangle"), [node_doc("sop", "attribwrangle")], ("vex", "wrangle", "code"), True, True, "medium"),
        ToolSpec("set_wrangle_code", "vex", "Replace and optionally compile-check VEX on a wrangle.", SetWrangleArgs, remote("set_wrangle_code"), [node_doc("sop", "attribwrangle")], ("vex", "wrangle", "compile"), True, True, "medium"),
        ToolSpec("get_geometry_info", "geometry", "Summarize counts, bounds, attributes and groups.", NodePathArgs, remote("get_geometry_info"), [hom("hou/Geometry.txt", "hou.Geometry")], ("geometry", "attributes", "bounding box", "counts")),
        ToolSpec("get_geometry_data", "geometry", "Read paginated point or primitive attribute values.", GeometryDataArgs, remote("get_geometry_data"), [hom("hou/Geometry.txt", "hou.Geometry")], ("points", "primitives", "attributes", "data")),
        ToolSpec("render_single_view", "render", "Render one generated view.", RenderSingleArgs, remote("render_single_view"), [hom("hou/GeometryViewport.txt", "hou.GeometryViewport")], ("render", "viewport", "image"), True, True, "medium"),
        ToolSpec("render_quad_views", "render", "Render four orthographic or perspective views.", RenderQuadArgs, remote("render_quad_view"), [hom("hou/GeometryViewport.txt", "hou.GeometryViewport")], ("render", "quad", "views"), True, True, "medium"),
        ToolSpec("render_specific_camera", "render", "Render from an existing camera node.", RenderCameraArgs, remote("render_specific_camera"), [hom("hou/ObjNode.txt", "hou.ObjNode")], ("render", "camera", "image"), True, True, "medium"),
        ToolSpec("get_node_info", "node", "Inspect node type, position, flags, parameters and connections.", NodePathArgs, remote("get_node_info"), [hom("hou/OpNode.txt", "hou.OpNode")], ("node", "inspect", "connections")),
        ToolSpec("modify_node", "node", "Rename, move, or update an existing node.", ModifyNodeArgs, remote("modify_node"), [hom("hou/OpNode.txt", "hou.OpNode")], ("rename", "position", "modify"), True, True, "medium"),
        ToolSpec("set_material", "material", "Create or reuse a material and assign it to an OBJ node.", SetMaterialArgs, remote("set_material"), [node_doc("shop", "principledshader"), hom("hou/OpNode.txt", "hou.OpNode.createNode")], ("material", "shader", "principled"), True, True, "medium"),
        ToolSpec("find_nodes", "node", "Find nodes by root, name glob and live node type.", FindNodesArgs, remote("find_nodes"), [hom("hou/OpNode.txt", "hou.OpNode.allSubChildren")], ("find", "search", "node", "type")),
        ToolSpec("get_hip_info", "scene_file", "Inspect the current HIP file path and unsaved state.", NoArgs, remote("get_hip_info"), [hom("hou/hipFile.txt", "hou.hipFile")], ("hip", "file", "unsaved")),
        ToolSpec("save_hip", "scene_file", "Save the current HIP file with overwrite protection.", SaveHipArgs, remote("save_hip"), [hom("hou/hipFile.txt", "hou.hipFile.save")], ("hip", "save", "file"), True, False, "medium"),
    ]

    opus_specs = [
        ToolSpec("opus_get_model_names", "opus", "List OPUS procedural model names.", NoArgs, local("opus_get_model_names"), [hom("hou/OpNode.txt", "hou.OpNode")], ("opus", "assets", "models"), availability=opus_availability),
        ToolSpec("opus_get_model_params_schema", "opus", "Get the OPUS parameter schema for a structure.", OpusStructureArgs, local("opus_get_model_params_schema"), [hom("hou/ParmTemplate.txt", "hou.ParmTemplate")], ("opus", "schema", "parameters"), availability=opus_availability),
        ToolSpec("opus_create_model", "opus", "Submit an OPUS model generation job.", OpusCreateArgs, local("opus_create_model"), [hom("hou/OpNode.txt", "hou.OpNode")], ("opus", "create", "model"), True, False, "medium", availability=opus_availability),
        ToolSpec("opus_variate_model", "opus", "Submit OPUS model variations.", OpusVariateArgs, local("opus_variate_model"), [hom("hou/OpNode.txt", "hou.OpNode")], ("opus", "variation", "model"), True, False, "medium", availability=opus_availability),
        ToolSpec("opus_check_job_status", "opus", "Check an OPUS batch job.", OpusJobArgs, local("opus_check_job_status"), [hom("hou/OpNode.txt", "hou.OpNode")], ("opus", "job", "status"), availability=opus_availability),
        ToolSpec("opus_import_model_url", "opus", "Download and import an OPUS model archive.", OpusImportArgs, local("opus_import_model_url"), [hom("hou/hipFile.txt", "hou.hipFile")], ("opus", "import", "download"), True, True, "high", availability=opus_availability),
    ]

    for spec in specs + opus_specs:
        registry.register(spec)
    return registry
