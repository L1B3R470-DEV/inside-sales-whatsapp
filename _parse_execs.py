import sqlite3, json
from typing import Any

def revive(root):
    def _revive(node):
        if isinstance(node, str) and node.isdigit():
            idx = int(node)
            if 0 <= idx < len(root):
                return _revive(root[idx])
        if isinstance(node, list):
            return [_revive(x) for x in node]
        if isinstance(node, dict):
            return {k:_revive(v) for k,v in node.items()}
        return node
    return _revive(root[0])

p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
for eid, status in cur.execute("select id,status from execution_entity order by id desc limit 5").fetchall():
    row=cur.execute("select data from execution_data where executionId=?", (eid,)).fetchone()
    print('EXEC', eid, status)
    if not row:
        print('no data')
        continue
    raw=row[0]
    try:
        arr=json.loads(raw)
        data=revive(arr)
        rd=data.get('resultData', {})
        ed=data.get('executionData', {})
        print('resultData_keys', list(rd.keys()))
        if 'error' in rd:
            print('error', rd['error'])
        if 'runData' in rd:
            print('runData_nodes', list(rd['runData'].keys())[:20])
        stack=ed.get('nodeExecutionStack') or []
        print('stack_len', len(stack))
        if stack:
            top=stack[-1]
            print('top_node', top.get('node',{}).get('name'), top.get('node',{}).get('type'))
        meta=ed.get('metadata') or {}
        print('metadata', meta)
    except Exception as e:
        print('parse_error', e)
    print('-----')
conn.close()
