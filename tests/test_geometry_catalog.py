"""Framed TCP + catalog geometry observation test against an isolated host."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import houdini_mcp_server as bridge
bridge._houdini_port = int(sys.argv[1])
bridge._houdini_connection = None


def call(tool_name, **args):
    result = bridge.tool_registry.invoke(tool_name, args)
    assert result['status'] == 'success', result
    return result['result']


root = call('create_node',parent_path='/obj',node_type='geo',name='MCP_GEOMETRY_CATALOG_TEST')['path']
try:
    box = call('create_node',parent_path=root,node_type='box',name='source')['path']
    transform = call('create_node',parent_path=root,node_type='xform',name='edit')['path']
    call('connect_nodes',from_path=box,to_path=transform)
    before = call('capture_geometry_snapshot',path=transform,attributes=['P'],allow_cook=True)
    call('set_parameters',path=transform,parameters={'t':[2.0,0.0,0.0]})
    after = call('capture_geometry_snapshot',path=transform,attributes=['P'],allow_cook=True)
    diff = call('compare_geometry_snapshots',before_id=before['snapshot_id'],after_id=after['snapshot_id'],assume_index_correspondence=True)
    assert diff['comparable'] and diff['topology_equal'], diff
    assert diff['attributes'][0]['max_absolute_delta'] == 2.0, diff
    assert diff['attributes'][0]['changed_rows'] == 8, diff
    page = call('get_geometry_snapshot_data',snapshot_id=before['snapshot_id'],limit=3)
    assert page['count'] == 3 and page['next_start'] == 3, page
    vertices = call('get_geometry_data',path=box,element='vertices',attributes=[],limit=2)
    assert 'point_number' in vertices['data'][0], vertices
    detail = call('get_geometry_data',path=box,element='detail',attributes=[])
    assert detail['count'] == 1, detail
    call('release_geometry_snapshot',snapshot_id=before['snapshot_id'])
    missing = bridge.tool_registry.invoke('get_geometry_snapshot_data',{'snapshot_id':before['snapshot_id']})
    assert missing['status'] == 'error' and missing['origin'] == 'houdini', missing
    print('ALL GEOMETRY CATALOG/TCP TESTS PASSED')
finally:
    call('delete_node',path=root)
    bridge._houdini_connection.disconnect()
