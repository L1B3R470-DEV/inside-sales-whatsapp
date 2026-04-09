import sqlite3, json
p='/data/database.sqlite'
conn=sqlite3.connect(p)
cur=conn.cursor()
for eid, status in cur.execute("select id,status from execution_entity order by id desc limit 3").fetchall():
    row=cur.execute("select data from execution_data where executionId=?", (eid,)).fetchone()
    print('EXEC', eid, status)
    if not row:
        print('no execution_data')
        continue
    raw=row[0]
    try:
        data=json.loads(raw)
    except Exception as e:
        print('json_load_error', e)
        print(raw[:1000])
        continue
    try:
        resultData = data[2]
        executionData = data[3]
        print('resultData_keys', list(resultData.keys()) if isinstance(resultData, dict) else type(resultData))
        print('executionData_keys', list(executionData.keys()) if isinstance(executionData, dict) else type(executionData))
    except Exception as e:
        print('shape_error', e)
    txt=raw
    for needle in ['errorMessage','lastNodeExecuted','Task request timed out','Offer expired','problem executing the workflow']:
        if needle in txt:
            print('FOUND', needle)
    print('snippet', txt[:4000])
    print('-----')
conn.close()
