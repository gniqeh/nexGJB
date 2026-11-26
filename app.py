import json, os, copy
from pathlib import Path
from collections import Counter
from fastapi import FastAPI, HTTPException
from fastapi.responses import Response, FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from shapely.geometry import shape, mapping
from shapely.ops import transform
from pyproj import Transformer
from urllib.parse import quote
ROOT=Path(__file__).resolve().parent
LEVELS=('province','city','county')
CRS={'WGS84':4326,'CGCS2000':4490,'L-EST97':3301}
app=FastAPI()
features={}; maps={}

def load():
    path=Path(os.environ.get('GEOJSON_FILE',str(ROOT/'data/china.geojson')))
    if not path.is_file(): raise RuntimeError(f'请放入数据文件: {path}')
    data=json.loads(path.read_text(encoding='utf-8-sig'))
    if data.get('type')!='FeatureCollection': raise ValueError('需要 FeatureCollection')
    source_crs=data.get('crs')
    if source_crs and not any(x in str(source_crs).upper() for x in ('4326','CRS84')): raise ValueError('输入必须为 WGS84 经纬度')
    for f in data['features']:
        p=f['properties']; lev=p['level']
        if lev not in LEVELS: continue
        key=(lev,str(p['feature_id']))
        if key in features: raise ValueError(f'同层级 ID 重复: {key}')
        if not p.get('province') or (lev=='city' and not p.get('city')) or (lev=='county' and not p.get('county')): raise ValueError(f'缺少行政区字段: {key}')
        g=shape(f['geometry'])
        if g.is_empty or g.geom_type not in ('Polygon','MultiPolygon'): raise ValueError(f'非有效面类型: {key}')
        if not (-180<=g.bounds[0]<=g.bounds[2]<=180 and -90<=g.bounds[1]<=g.bounds[3]<=90): raise ValueError(f'坐标超出经纬度范围: {key}')
        features[key]=f
    for lev in LEVELS:
        out=[]
        for (l,id),f in features.items():
            if l!=lev: continue
            p=f['properties']; g=shape(f['geometry']).simplify({'province':.025,'city':.012,'county':.005}[lev],preserve_topology=True)
            name=p[{'province':'province','city':'city','county':'county'}[lev]]
            out.append({'type':'Feature','properties':{'key':id,'name':name,'province':p.get('province'),'city':p.get('city')},'geometry':mapping(g)})
        maps[lev]=json.dumps({'type':'FeatureCollection','features':out},ensure_ascii=False,separators=(',',':')).encode()
    print('已加载:',Counter(k[0] for k in features))

@app.on_event('startup')
def startup():
    features.clear(); maps.clear(); load()

@app.get('/api/map/{level}')
def map_data(level:str):
    if level not in maps: raise HTTPException(404,'未知层级')
    return Response(maps[level],media_type='application/geo+json')

class Export(BaseModel):
    mode:str
    level:str
    ids:list[str]
    target:str|None=None
    crs:str='WGS84'

def select(r):
    if r.level not in LEVELS or r.crs not in CRS or not r.ids: raise HTTPException(400,'参数无效')
    keys=list(dict.fromkeys((r.level,i) for i in r.ids))
    if any(k not in features for k in keys): raise HTTPException(400,'区域不存在')
    chosen=[features[k] for k in keys]
    if r.mode=='point': return chosen
    if r.mode!='area' or len(keys)!=1 or (r.level,r.target) not in [('province','city'),('province','county'),('city','county')]: raise HTTPException(400,'提取范围无效')
    p=chosen[0]['properties']
    return [f for (l,_),f in features.items() if l==r.target and f['properties'].get('province')==p['province'] and (r.level=='province' or f['properties'].get('city')==p['city'])]

@app.post('/api/preview')
def preview(r:Export):
    return {'count':len(select(r))}

@app.post('/api/export')
def export(r:Export):
    chosen=select(r)
    if not chosen: raise HTTPException(400,'没有符合条件的行政区')
    result={'type':'FeatureCollection','features':[]}
    epsg=CRS[r.crs]
    if epsg!=4326:
        t=Transformer.from_crs(4326,epsg,always_xy=True)
        result['crs']={'type':'name','properties':{'name':f'urn:ogc:def:crs:EPSG::{epsg}'}}
    for f in chosen:
        item=copy.deepcopy(f)
        if epsg!=4326:
            item['geometry']=mapping(transform(lambda x,y,z=None:t.transform(x,y,errcheck=True),shape(f['geometry'])))
            item.pop('bbox',None)
        result['features'].append(item)
    name=f'行政区划_{r.target or r.level}_{r.crs}_{len(chosen)}.geojson'
    return Response(json.dumps(result,ensure_ascii=False,allow_nan=False,separators=(',',':')),media_type='application/geo+json',headers={'Content-Disposition':"attachment; filename*=UTF-8''"+quote(name)})

app.mount('/static',StaticFiles(directory=ROOT/'static'),name='static')
@app.get('/')
def index(): return FileResponse(ROOT/'static/index.html')
