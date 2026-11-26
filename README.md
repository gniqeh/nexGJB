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

## v1.1
地图工具栏新增“只看黑龙江”，仅显示黑龙江当前层级并自动定位；标签采用面内代表点、屏幕碰撞过滤，放大可显示更多名称。切换范围会确认清空已有选择。
下载确认窗口支持 GeoJSON、GeoPackage、Shapefile ZIP、KML、GeoParquet、CSV+WKT、FlatGeobuf。KML 固定 WGS84；CSV 带 EPSG 字段；Shapefile 受 DBF 字段限制，完整属性建议使用 GeoPackage。
升级后运行 bash install.sh 更新依赖，再重启 systemd 服务。无需修改端口或 Nginx。

## v1.2 后台使用日志
不修改前端、不增加依赖、不使用数据库。首页 GET 访问和进入导出处理器的成功/失败事件经有界队列非阻塞投递，由独立线程写入 logs/visits/YYYY-MM.jsonl 和 logs/downloads/YYYY-MM.jsonl。按月分文件，永久保留，无自动清理。默认单 Uvicorn worker；日志故障、队列满、强制关机可能造成少量记录丢失，但不会阻止正常请求。正常停机最多等待三秒排空队列。成功生成不代表客户端已保存；框架在进入导出处理器前拒绝的非法请求不计入。IP 使用 ASGI client 地址，独立 IP 不等于人数。日志包含 IP、浏览器 User-Agent（访问）和下载选择信息，请限制管理员访问并按院内要求告知使用者。新目录权限 0700、文件 0600；备份日志并监控磁盘空间。日志不进入 Git。

```bash
python3 stats.py --all
python3 stats.py --today
python3 stats.py --month 2026-11
python3 stats.py --year 2026
```

仅需拉取代码并重启 nexgjb 服务，不需要再次安装环境。统计脚本只使用 Python 标准库，可在服务运行时读取日志。
