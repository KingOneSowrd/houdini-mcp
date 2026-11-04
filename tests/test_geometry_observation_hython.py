"""Run with hython. Creates only a temporary network in this isolated process."""
import json
from pathlib import Path
import sys
import unittest
import hou
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from houdinimcp_runtime.server import HoudiniMCPServer

CODE = """
node=hou.pwd(); g=node.geometry(); g.clear()
g.addAttrib(hou.attribType.Point, 'id', 0)
g.addAttrib(hou.attribType.Vertex, 'uv', (0.,0.,0.))
g.addAttrib(hou.attribType.Global, 'label', 'reference')
g.addAttrib(hou.attribType.Global, 'metadata', {})
g.setGlobalAttribValue('label', 'reference')
g.setGlobalAttribValue('metadata', {'nested': [1, 2]})
g.addArrayAttrib(hou.attribType.Global, 'weights', hou.attribData.Float)
g.setGlobalAttribValue('weights', tuple(float(i) for i in range(10)))
points=g.createPoints(((0,0,0),(1,0,0),(0,1,0),(1,1,0)))
for i,p in enumerate(points):p.setAttribValue('id', i+10)
for pi,indices in enumerate(((0,1,2),(0,2,3))):
 face=g.createPolygon()
 for vi,index in enumerate(indices):
  v=face.addVertex(points[index]); v.setAttribValue('uv',(float(pi),float(vi),0.))
"""


class GeometryHythonTests(unittest.TestCase):
    def setUp(self):
        self.server = HoudiniMCPServer()
        self.root = hou.node('/obj').createNode('geo', 'MCP_GEOMETRY_TEST')
        self.source = self.root.createNode('python', 'source')
        self.source.parm('python').set(CODE)
        self.source.cook(force=True)
        self.assertFalse(self.source.errors())

    def tearDown(self):
        self.root.destroy()

    def call(self, name, **params):
        result = self.server._execute_command_internal({'type': name, 'params': params})
        self.assertEqual(result['status'], 'success', result)
        json.dumps(result, allow_nan=False)
        return result['result']

    def capture(self, node=None, **params):
        return self.call('capture_geometry_snapshot', path=(node or self.source).path(), **params)['snapshot_id']

    def test_vertex_seam_and_detail_values(self):
        page = self.call('get_geometry_data', path=self.source.path(), element='vertices', attributes=['uv'], limit=6)
        shared = [r for r in page['data'] if r['point_number']==0]
        self.assertEqual(len(shared), 2)
        self.assertNotEqual(shared[0]['uv'], shared[1]['uv'])
        self.assertEqual(shared[0]['vertex_index'], 0)
        detail = self.call('get_geometry_data', path=self.source.path(), element='detail', attributes=['label','metadata','weights'], max_value_items=3)
        self.assertEqual(detail['data'][0]['label'], 'reference')
        self.assertEqual(detail['data'][0]['metadata'], {'nested': [1,2]})
        self.assertEqual(detail['data'][0]['weights'], [0.,1.,2.])
        self.assertEqual(detail['truncated_values'], 1)
        self.assertIsNone(detail['next_start'])
        self.assertEqual(self.call('get_geometry_data',path=self.source.path(),element='detail',start=1)['data'], [])

    def test_snapshot_immutable_pages_and_uv_diff(self):
        old = self.capture(element='vertices', attributes=['uv'])
        page = self.call('get_geometry_snapshot_data',snapshot_id=old,limit=2)
        original = page['data']
        self.source.parm('python').set(CODE + "\nfor p in g.prims():\n for v in p.vertices(): v.setAttribValue('uv',(9.,0.,0.))")
        with self.assertRaisesRegex(ValueError,'clean/cooked'):
            self.capture(element='vertices',attributes=['uv'])
        new = self.capture(element='vertices',attributes=['uv'],allow_cook=True)
        self.assertEqual(self.call('get_geometry_snapshot_data',snapshot_id=old,limit=2)['data'],original)
        diff = self.call('compare_geometry_snapshots',before_id=old,after_id=new,assume_index_correspondence=True)
        self.assertTrue(diff['comparable'])
        self.assertEqual(diff['attributes'][0]['changed_rows'],6)
        self.assertFalse(diff['equal_selected_values'])
        self.assertEqual(self.call('get_geometry_snapshot_data',snapshot_id=old,start=page['next_start'],limit=2)['start'],2)
        self.call('release_geometry_snapshot',snapshot_id=old)
        with self.assertRaisesRegex(ValueError,'unavailable'):
            self.call('get_geometry_snapshot_data',snapshot_id=old)

    def test_frame_output_port_and_no_global_frame_change(self):
        xform=self.root.createNode('xform');xform.setInput(0,self.source)
        xform.parm('tx').setExpression('$F')
        current=hou.frame()
        values=self.call('get_geometry_data',path=xform.path(),frame=7,attributes=['P'])
        self.assertEqual(values['data'][0]['P'][0],7.)
        self.assertEqual(hou.frame(),current)
        subnet=self.root.createNode('subnet')
        box=subnet.createNode('box')
        moved=subnet.createNode('xform');moved.setInput(0,box);moved.parm('tx').set(5)
        out0=subnet.createNode('output');out0.setInput(0,box);out0.parm('outputidx').set(0)
        out1=subnet.createNode('output');out1.setInput(0,moved);out1.parm('outputidx').set(1)
        a=self.call('get_geometry_data',path=subnet.path(),output_index=0)
        b=self.call('get_geometry_data',path=subnet.path(),output_index=1)
        self.assertAlmostEqual(b['data'][0]['P'][0]-a['data'][0]['P'][0],5.)
        with self.assertRaisesRegex(ValueError,'allow_cook'):
            self.capture(subnet,output_index=1)

    def test_keyed_comparison_partial_capture_and_empty(self):
        a=self.capture(attributes=['P','id'])
        xform=self.root.createNode('xform');xform.setInput(0,self.source);xform.parm('tx').set(1)
        b=self.capture(xform,attributes=['P','id'],allow_cook=True)
        diff=self.call('compare_geometry_snapshots',before_id=a,after_id=b,key_attribute='id')
        self.assertEqual(diff['matched_rows'],4)
        self.assertEqual(diff['attributes'][0]['max_absolute_delta'],1.)
        partial=self.capture(attributes=['P','id'],max_elements=2)
        result=self.call('compare_geometry_snapshots',before_id=a,after_id=partial,key_attribute='id')
        self.assertFalse(result['rows_complete'])
        self.assertFalse(result['equal_selected_values'])
        self.source.parm('python').set('hou.pwd().geometry().clear()')
        empty=self.capture(attributes=['P'],allow_cook=True)
        result=self.call('get_geometry_snapshot_data',snapshot_id=empty)
        self.assertEqual(result['source_total'],0)
        self.assertEqual(result['data'],[])

    def test_byte_bounds_and_eviction(self):
        self.source.parm('python').set("g=hou.pwd().geometry();g.clear();g.createPoints(tuple((float(i),0.,0.) for i in range(1000)))")
        result=self.call('capture_geometry_snapshot',path=self.source.path(),allow_cook=True,max_bytes=4096)
        self.assertLessEqual(result['stored_bytes'],4096)
        self.assertFalse(result['rows_complete'])
        self.assertGreater(result['count'],0)
        self.assertLess(result['count'],1000)
        first=result['snapshot_id']
        for _ in range(8):
            last=self.call('capture_geometry_snapshot',path=self.source.path(),max_elements=2)
        self.assertEqual(len(self.server._geometry_snapshots.items),8)
        with self.assertRaisesRegex(ValueError,'unavailable'):
            self.call('get_geometry_snapshot_data',snapshot_id=first)
        self.assertTrue(last['evicted_snapshot_ids'])

    def test_detail_compare_nonfinite_and_schema(self):
        old=self.capture(element='detail',attributes=['label'])
        self.source.parm('python').set(CODE + "\ng.setGlobalAttribValue('label','changed')\ng.addAttrib(hou.attribType.Point,'invalid',0.)\nfor p in g.points(): p.setAttribValue('invalid',float('nan'))")
        new=self.capture(element='detail',attributes=['label'],allow_cook=True)
        result=self.call('compare_geometry_snapshots',before_id=old,after_id=new)
        self.assertEqual(result['schema_added'][0]['name'],'invalid')
        self.assertEqual(result['attributes'][0]['changed_rows'],1)
        values=self.call('get_geometry_data',path=self.source.path(),attributes=['invalid'])
        self.assertEqual(values['data'][0]['invalid'],{'__nonfinite__':'nan'})
        with self.assertRaisesRegex(ValueError,'not found'):
            self.call('get_geometry_data',path=self.source.path(),element='vertices',attributes=['missing'])


if __name__=='__main__':
    unittest.main(verbosity=2)
