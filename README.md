# nexGJB
**Next Generation GeoJSON Boundary**

内网行政区划边界提取工具。点选模式（省、市、县多选）及大区域模式（省、市单选，提取指定下级），仅展示当前层级，不依赖在线底图。

## 安装

需要预先安装 micromamba、mamba 或 conda。使用 conda-forge 和 Python 3.12，环境名 nexgjb。

```bash
bash install.sh micromamba
# 或 bash install.sh mamba / bash install.sh conda
PORT=8812 bash start.sh
```

不指定安装参数时自动检测环境管理器。无需手动激活。首次安装需要联网下载依赖和 Leaflet 1.9.4，运行期不需要外网。

## 数据
将 WGS84 FeatureCollection 放入 data/china.geojson，或通过 GEOJSON_FILE 指定路径。属性需要 feature_id、level (province/city/county)、province、city、county；同层级 ID 唯一。省直辖县按 province 匹配，市级下辖按 province + city 匹配。请确保源数据父子关系准确。
本仓库暂不包含行政区划数据。数据目录允许后续手动提交数据。

地图使用独立简化几何，可能出现微小显示缝隙；下载保留原始精度和属性。数据更新后重启。大区域模式仅输出目标层级。WGS84 为标准 GeoJSON；CGCS2000 (4490) 与 L-EST97 (3301) 使用旧式 CRS 扩展。后者适用范围为爱沙尼亚，不应用于中国的距离与面积测算。

访问 http://服务器IP:8812。仅部署于可信内网。可选 systemd：编辑 nexgjb.service.example 的用户、路径、环境管理器及端口后安装。未经真实全国数据和浏览器端到端验证。
