import csv, io, json, tempfile, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import geopandas as gpd
from shapely.geometry import shape, MultiPolygon

FORMATS={'geojson','gpkg','shp','kml','parquet','csv','fgb'}

def write_export(features,epsg,fmt):
    rows=[dict(f['properties']) for f in features]
    geoms=[shape(f['geometry']) for f in features]
    geoms=[MultiPolygon([g]) if g.geom_type=='Polygon' else g for g in geoms]
    if fmt=='csv':
        out=io.StringIO()
        fields=list(dict.fromkeys(k for r in rows for k in r))
        if 'geometry_wkt' in fields or 'crs_epsg' in fields: raise ValueError('属性与导出字段冲突')
        w=csv.DictWriter(out,fieldnames=fields+['geometry_wkt','crs_epsg'])
        w.writeheader()
        for r,g in zip(rows,geoms): w.writerow(dict(r,geometry_wkt=g.wkt,crs_epsg=epsg))
        return out.getvalue().encode('utf-8-sig'),'.csv','text/csv'
    if fmt=='kml':
        if epsg!=4326: raise ValueError('KML 需要 WGS84')
        ns='http://www.opengis.net/kml/2.2'
        ET.register_namespace('',ns)
        def add(parent,tag,value=None):
            node=ET.SubElement(parent,'{'+ns+'}'+tag)
            if value is not None: node.text=str(value)
            return node
        root=ET.Element('{'+ns+'}kml'); doc=add(root,'Document')
        from shapely.geometry.polygon import orient
        for r,g in zip(rows,geoms):
            pm=add(doc,'Placemark'); add(pm,'name',r.get(r.get('level',''), '') or r.get('feature_id',''))
            data=add(pm,'ExtendedData')
            for k,v in r.items():
                d=add(data,'Data'); d.set('name',k); add(d,'value','' if v is None else v)
            multi=add(pm,'MultiGeometry')
            for poly in g.geoms:
                poly=orient(poly,sign=1.0); p=add(multi,'Polygon')
                for tag,ring in [('outerBoundaryIs',poly.exterior)]+[('innerBoundaryIs',i) for i in poly.interiors]:
                    lr=add(add(p,tag),'LinearRing'); add(lr,'coordinates',' '.join(f'{x},{y}' for x,y,*_ in ring.coords))
        return ET.tostring(root,encoding='utf-8',xml_declaration=True),'.kml','application/vnd.google-earth.kml+xml'
    df=gpd.GeoDataFrame(rows,geometry=geoms,crs=f'EPSG:{epsg}')
    with tempfile.TemporaryDirectory() as tmp:
        d=Path(tmp)
        if fmt=='parquet':
            p=d/'boundary.parquet'; df.to_parquet(p,index=False)
            return p.read_bytes(),'.parquet','application/octet-stream'
        if fmt=='shp':
            if any(len(k.encode('utf-8'))>10 for k in df.columns if k!='geometry'): raise ValueError('Shapefile 字段名超过 10 字节，请选择 GeoPackage')
            p=d/'boundary.shp'; df.to_file(p,driver='ESRI Shapefile',encoding='UTF-8',index=False,engine='pyogrio')
            out=io.BytesIO()
            with zipfile.ZipFile(out,'w',zipfile.ZIP_DEFLATED) as z:
                for item in sorted(d.glob('boundary.*')): z.write(item,item.name)
            return out.getvalue(),'.zip','application/zip'
        ext,driver,mime={'gpkg':('.gpkg','GPKG','application/geopackage+sqlite3'),'fgb':('.fgb','FlatGeobuf','application/octet-stream')}[fmt]
        p=d/('boundary'+ext)
        df.to_file(p,driver=driver,index=False,engine='pyogrio')
        return p.read_bytes(),ext,mime
