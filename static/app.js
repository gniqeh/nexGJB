const $=id=>document.getElementById(id), levelNames={province:'省级',city:'市级',county:'县级'};
const state={mode:'point',level:'city',selected:new Map(),target:'',completed:false,hlj:false};
const map=L.map('realmap',{zoomControl:false,attributionControl:false,preferCanvas:true}).setView([35,104],4);
let layer=null, generation=0, busy=false; const labels=L.layerGroup().addTo(map);
function updateLabels(){labels.clearLayers();if(!state.hlj||!layer)return;const occupied=[],size=map.getSize();const entries=[];layer.eachLayer(l=>{const p=l.feature.properties;if(!p.label)return;const latlng=L.latLng(p.label[1],p.label[0]),pt=map.latLngToContainerPoint(latlng);if(pt.x<0||pt.y<0||pt.x>size.x||pt.y>size.y)return;entries.push({p,latlng,pt,priority:state.selected.has(p.key)?1:0})});entries.sort((a,b)=>b.priority-a.priority);for(const {p,latlng,pt} of entries){const w=String(p.name).length*12+10,h=19;const box=[pt.x-w/2,pt.y-h/2,pt.x+w/2,pt.y+h/2];if(occupied.some(b=>box[0]<b[2]&&box[2]>b[0]&&box[1]<b[3]&&box[3]>b[1]))continue;occupied.push(box);const el=document.createElement('span');el.textContent=p.name;L.marker(latlng,{interactive:false,keyboard:false,icon:L.divIcon({className:'region-label',html:el,iconSize:[w,h],iconAnchor:[w/2,h/2]})}).addTo(labels)}}
map.on('moveend zoomend resize',updateLabels); const cache={};
function toast(msg){const t=$('toast');t.textContent=msg;t.classList.add('show');setTimeout(()=>t.classList.remove('show'),3500)}
function style(f){const s=state.selected.has(f.properties.key);return {color:s?'#167d70':'#819991',weight:s?2:0.8,fillColor:s?'#33a78d':'#cbdad4',fillOpacity:s?0.85:0.55}}
function reset(){state.selected.clear();state.target='';state.completed=false}
function discard(){return !state.selected.size||confirm('当前已选区域及提取设置将被清空，是否继续？')}
async function loadMap(){
 const n=++generation,lev=state.level;labels.clearLayers();if(layer){map.removeLayer(layer);layer=null}
 try{if(!cache[lev]){const r=await fetch('/api/map/'+lev);if(!r.ok)throw Error('地图加载失败');cache[lev]=await r.json()}
 if(n!==generation)return;
 layer=L.geoJSON(cache[lev],{filter:f=>!state.hlj||['黑龙江省','黑龙江'].includes(f.properties.province),style,onEachFeature(f,l){const p=f.properties,tip=document.createElement('span');tip.textContent=[p.province,lev==='county'?p.city:null,p.name].filter((v,i,a)=>v&&a.indexOf(v)===i).join(' / ');l.bindTooltip(tip,{sticky:true});l.on('click',()=>{if(busy)return;if(state.mode==='area'){if(state.selected.has(p.key)){reset()}else{if(!discard())return;reset();state.selected.set(p.key,p.name)}}else{if(state.selected.has(p.key))state.selected.delete(p.key);else state.selected.set(p.key,p.name);state.completed=false}render()})}}).addTo(map);
 if(layer.getBounds().isValid())map.fitBounds(layer.getBounds(),{padding:[25,25]});updateLabels();
 }catch(e){if(n===generation)toast(e.message)}
}
function render(){
 const area=state.mode==='area';
 document.querySelectorAll('.mode-btn').forEach(b=>b.classList.toggle('active',b.dataset.mode===state.mode));
 document.querySelectorAll('.level-btn').forEach(b=>{b.classList.toggle('active',b.dataset.level===state.level);b.classList.toggle('hidden',area&&b.dataset.level==='county')});
 $('levelTitle').textContent=area?'选择区域层级':'选择行政区层级';$('selectTitle').textContent=area?'选择一个大区域':'选择行政区';
 $('mapInstruction').textContent=area?'点击地图选择一个区域':'点击地图选择多个区域，再次点击取消';
 $('mapHint').textContent=(area?'大区域模式 · 单选':'点选模式 · 多选')+' · '+levelNames[state.level];
 $('emptyText').style.display=state.selected.size?'none':'block';$('chips').replaceChildren();
 for(const [id,name] of state.selected){let c=document.createElement('span');c.className='chip';c.textContent=name;let b=document.createElement('button');b.textContent='×';b.onclick=()=>{if(busy)return;state.selected.delete(id);state.completed=false;state.target='';render()};c.append(b);$('chips').append(c)}
 $('mapCount').textContent='已选择 '+state.selected.size+' 个区域';$('completeBtn').disabled=busy||!state.selected.size;$('clearBtn').disabled=busy||!state.selected.size;
 $('downloadBtn').disabled=busy||!state.completed||(area&&!state.target);
 $('targetSection').classList.toggle('hidden',!area||!state.completed);$('crsStep').textContent=area?'4':'3';$('targetOptions').replaceChildren();
 if(area&&state.completed){for(const v of state.level==='province'?['city','county']:['county']){let b=document.createElement('button');b.textContent=levelNames[v];b.classList.toggle('active',state.target===v);b.onclick=()=>{if(busy)return;state.target=v;render()};$('targetOptions').append(b)}}if(layer)layer.setStyle(style);updateLabels()
}
document.querySelectorAll('.mode-btn').forEach(b=>b.onclick=()=>{if(busy||b.dataset.mode===state.mode||!discard())return;reset();state.mode=b.dataset.mode;if(state.mode==='area'&&state.level==='county'){state.level='province';loadMap()}render()});
document.querySelectorAll('.level-btn').forEach(b=>b.onclick=()=>{if(busy||b.dataset.level===state.level||!discard())return;reset();state.level=b.dataset.level;render();loadMap()});
$('scopeBtn').onclick=()=>{if(busy||!discard())return;reset();state.hlj=!state.hlj;$('scopeBtn').setAttribute('aria-pressed',String(state.hlj));$('scopeBtn').textContent=state.hlj?'返回全国':'只看黑龙江';render();loadMap()};
$('clearBtn').onclick=()=>{if(!busy&&discard()){reset();render()}};$('completeBtn').onclick=()=>{if(busy)return;state.completed=true;render();if(state.mode==='point')openConfirm()};
function payload(){return {mode:state.mode,level:state.level,ids:[...state.selected.keys()],target:state.target||null,crs:document.querySelector('input[name=crs]:checked').value}}
document.querySelectorAll('input[name=crs]').forEach(r=>r.onchange=()=>document.querySelectorAll('.coord-option').forEach(x=>x.classList.toggle('selected',x.querySelector('input').checked)));
async function request(url,p){const r=await fetch(url,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(p)});if(!r.ok){let msg='请求失败';try{msg=(await r.json()).detail||msg}catch{}throw Error(typeof msg==='string'?msg:'参数无效')}return r}
let pending=null;
async function openConfirm(){if(busy||!state.completed||(state.mode==='area'&&!state.target))return;busy=true;render();try{let p=payload(),v=await(await request('/api/preview',p)).json();if(!v.count){toast('没有符合条件的下辖区域');return}pending=p;$('format').value='geojson';let text=['选择：'+[...state.selected.values()].join('、'),'输出层级：'+levelNames[p.target||p.level],'要素数量：'+v.count,'坐标系：'+p.crs];if(p.crs==='L-EST97')text.push('注意：该投影适用范围为爱沙尼亚，不适用于中国。');$('modalSummary').replaceChildren(...text.map(t=>{let d=document.createElement('div');d.textContent=t;return d}));updateFormat();$('confirmOverlay').classList.add('show')}catch(e){toast(e.message)}finally{busy=false;render()}}
function updateFormat(){if(!pending)return;const fmt=$('format').value;$('formatNote').textContent=fmt==='kml'?'KML 固定使用 WGS84，本次导出将自动转换。':fmt==='geojson'&&pending.crs!=='WGS84'?'非 RFC 7946 标准 GeoJSON，将附带 CRS 标记。':fmt==='shp'?'UTF-8 编码，ZIP 包含 SHP、SHX、DBF、PRJ、CPG。':fmt==='csv'?'包含 geometry_wkt 和 crs_epsg 字段。':''}
$('format').onchange=updateFormat;
$('downloadBtn').onclick=openConfirm;$('backBtn').onclick=()=>{if(!busy){pending=null;$('confirmOverlay').classList.remove('show')}};
$('confirmDownload').onclick=async()=>{if(!pending||busy)return;busy=true;$('confirmDownload').disabled=true;render();try{const r=await request('/api/export',{...pending,format:$('format').value,crs:$('format').value==='kml'?'WGS84':pending.crs}),blob=await r.blob(),url=URL.createObjectURL(blob),a=document.createElement('a'),header=r.headers.get('Content-Disposition')||'',match=header.match(/filename\*=UTF-8''([^;]+)/);a.href=url;a.download=match?decodeURIComponent(match[1]):'boundary.geojson';document.body.append(a);a.click();a.remove();setTimeout(()=>URL.revokeObjectURL(url),1000);$('confirmOverlay').classList.remove('show');pending=null;toast('已生成下载文件')}catch(e){toast(e.message)}finally{busy=false;$('confirmDownload').disabled=false;render()}};
$('zoomIn').onclick=()=>map.zoomIn();$('zoomOut').onclick=()=>map.zoomOut();$('resetView').onclick=()=>{if(layer&&layer.getBounds().isValid())map.fitBounds(layer.getBounds(),{padding:[25,25]})};render();loadMap();
