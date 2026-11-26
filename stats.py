"""Read-only CLI: no dependency on the web service or third-party packages."""
import argparse
import json
from collections import Counter
from datetime import datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parent/'logs'

def records(kind,prefix,errors):
    for path in sorted((ROOT/kind).glob('*.jsonl')):
        if prefix and not (path.stem.startswith(prefix) or prefix.startswith(path.stem)): continue
        try:
            with path.open('rb') as stream:
                for line in stream:
                    try:
                        row=json.loads(line)
                        if not isinstance(row,dict) or not isinstance(row.get('time'),str): raise ValueError()
                    except (ValueError,UnicodeError):
                        errors[0]+=1
                        continue
                    if row['time'].startswith(prefix): yield row
        except OSError:
            errors[0]+=1

def main():
    p=argparse.ArgumentParser(description='nexGJB 使用统计')
    g=p.add_mutually_exclusive_group()
    g.add_argument('--all',action='store_true')
    g.add_argument('--today',action='store_true')
    g.add_argument('--month',metavar='YYYY-MM')
    g.add_argument('--year',metavar='YYYY')
    a=p.parse_args()
    prefix=datetime.now().astimezone().strftime('%Y-%m-%d') if a.today else a.month or a.year or ''
    if a.month or a.year:
        try: datetime.strptime(prefix,'%Y-%m' if a.month else '%Y')
        except ValueError: p.error('日期格式无效')
    errors=[0]; visits=0; ips=set(); successes=0; failures=0; total=0
    formats=Counter(); regions=Counter(); crs=Counter()
    for row in records('visits',prefix,errors):
        visits+=1
        if row.get('ip'): ips.add(row['ip'])
    for row in records('downloads',prefix,errors):
        if row.get('status')!='generated':
            failures+=1
            continue
        successes+=1; total+=row.get('bytes',0)
        formats[row.get('format','unknown')]+=1; crs[row.get('crs','unknown')]+=1
        for item in row.get('selected',[]):
            name=' / '.join(str(v) for v in dict.fromkeys([item.get('province'),item.get('city'),item.get('county')]) if v)
            if name: regions[name]+=1
    print('========== nexGJB 使用统计 ==========')
    print('统计范围：',prefix or '全部历史')
    print('首页访问次数：',visits)
    print('首页独立 IP 数：',len(ips))
    print('成功生成次数：',successes)
    print('生成失败次数：',failures)
    print(f'生成文件体积：{total/1024**2:.2f} MiB')
    for title,c in [('文件格式',formats),('坐标系',crs),('热门选择区域（前20）',regions)]:
        print('\n'+title)
        for k,v in c.most_common(20): print(f'{k}: {v}')
    print('\n跳过的异常记录或不可读文件：',errors[0])
    print('注：独立 IP 不等于人数；成功生成不等于客户端保存成功。')

if __name__=='__main__': main()
