#!/usr/bin/env python3
"""优选 IP/域名列表节点名规范化（Clash 友好版）。

命名规则：
    地区节点   -> 香港01 / 日本-02 / 圣何塞03（同一城市有多家运营商时才带运营商）
    来源节点   -> 秋名山-电信 / 秋名山-三网
    无法识别   -> 秋名山-IP-01
    不带 emoji、不带延迟数字（延迟由客户端测速显示）。

用法：
    python3 clean.py cname.txt ip.txt                                  # 原地改写
    python3 clean.py --url <优选列表URL> --prefix QMS -o cname.txt --append   # 拉取远端合并
"""
import argparse
import os
import re
import sys
import urllib.request

REGION_CN = {
    'SG': '新加坡', 'JP': '日本', 'HK': '香港', 'TW': '台湾', 'KR': '韩国',
    'US': '美国', 'DE': '德国', 'GB': '英国', 'UK': '英国', 'NL': '荷兰',
    'FR': '法国', 'CA': '加拿大', 'AU': '澳大利亚', 'RU': '俄罗斯',
}

AIRPORT_CN = {
    'HKG': '香港', 'TPE': '台北', 'NRT': '东京', 'HND': '东京', 'KIX': '大阪',
    'SIN': '新加坡', 'SJC': '圣何塞', 'LAX': '洛杉矶', 'SEA': '西雅图',
    'FRA': '法兰克福', 'AMS': '阿姆斯特丹', 'LHR': '伦敦', 'CDG': '巴黎',
    'SYD': '悉尼', 'ICN': '首尔',
}

LABEL_CN = {
    '3NET': '三网', 'CT': '电信', 'CU': '联通', 'CMCC': '移动',
    'ASIA': '亚洲', 'NA': '美洲', 'EU': '欧洲', 'IP': 'IP',
}

OPS = ('移动', '联通', '电信')

PREFIX_CN = {'QMS': '秋名山'}

LINE_RE = re.compile(r'^(\[[0-9a-fA-F:]+\]|[\w.-]+)(:\d+)?$')


def detect_city(name):
    """机场三字码 / 英文地区码 / 中文城市名 -> 中文城市名。"""
    m = re.search(r'\b(HKG|TPE|NRT|HND|KIX|SIN|SJC|LAX|SEA|FRA|AMS|LHR|CDG|SYD|ICN)\b', name.upper())
    if m:
        return AIRPORT_CN[m.group(1)]
    m = re.search(r'\b(SG|JP|HK|TW|KR|US|DE|GB|UK|NL|FR|CA|AU|RU)\b', name.upper())
    if m:
        return REGION_CN[m.group(1)]
    cities = set(REGION_CN.values()) | set(AIRPORT_CN.values())
    for cn in sorted(cities, key=len, reverse=True):
        if cn in name:
            return cn
    return None


def detect_label(name):
    for cn in ('三网', '电信', '联通', '移动', '亚洲', '美洲', '欧洲'):
        if cn in name:
            return cn
    m = re.search(r'\b(3NET|CMCC|CT|CU|ASIA|NA|EU)\b', name.upper())
    return LABEL_CN[m.group(1)] if m else None


def is_promo(remark):
    return 'BestCF.pages.dev' in remark or 'WeTest优选' in remark


def clean(lines, prefix='QMS'):
    prefix_cn = PREFIX_CN.get(prefix.upper(), prefix)
    seen, city_items, other_groups = set(), {}, {}

    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        addr, _, remark = line.partition('#')
        addr = addr.strip()
        if not LINE_RE.match(addr):
            continue
        if is_promo(remark):
            continue
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)

        city = detect_city(remark)
        op = next((o for o in OPS if o in remark), None)
        if city:
            city_items.setdefault(city, []).append((addr, op))
        else:
            label = detect_label(remark)
            other_groups.setdefault(label or 'IP', []).append(addr)

    out = []
    for city, items in city_items.items():
        ops = {op for _, op in items if op}
        if len(ops) > 1:
            subgroups = {}
            for addr, op in items:
                subgroups.setdefault(op or '其他', []).append(addr)
            for op, addrs in subgroups.items():
                for i, addr in enumerate(addrs, 1):
                    out.append(f'{addr}#{city}{op}-{i:02d}')
        else:
            for i, (addr, _) in enumerate(items, 1):
                out.append(f'{addr}#{city}-{i:02d}')

    for label, addrs in other_groups.items():
        display = f'{prefix_cn}-{label}'
        for i, addr in enumerate(addrs, 1):
            name = display if len(addrs) == 1 else f'{display}-{i:02d}'
            out.append(f'{addr}#{name}')
    return out


def render(path, result):
    with open(path, 'w', encoding='utf-8') as f:
        f.write('\n'.join(result) + '\n')


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore').splitlines()


def main(argv):
    parser = argparse.ArgumentParser(description='优选列表节点名规范化')
    parser.add_argument('files', nargs='*', default=['cname.txt', 'ip.txt'])
    parser.add_argument('--url', help='从远程拉取并清洗')
    parser.add_argument('-o', '--out', help='配合 --url 使用的输出文件')
    parser.add_argument('--prefix', default='QMS', help='来源前缀（QMS -> 秋名山）')
    parser.add_argument('--append', action='store_true', help='配合 --url：追加到 -o 文件，已存在地址跳过')
    args = parser.parse_args(argv)

    if args.url:
        if not args.out:
            parser.error('--url 需要配合 -o/--out')
        result = clean(fetch(args.url), args.prefix)
        if args.append:
            existing = open(args.out, encoding='utf-8').read().splitlines() if os.path.exists(args.out) else []
            have = {line.partition('#')[0].strip().lower() for line in existing if line.strip()}
            result = [line for line in existing if line.strip()] + [
                line for line in result if line.partition('#')[0].strip().lower() not in have
            ]
        render(args.out, result)
        print(f'{args.out}: {len(result)} 条')
        return

    for path in args.files:
        with open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
        result = clean(lines, args.prefix)
        render(path, result)
        print(f'{path}: {len(lines)} 行 -> {len(result)} 条')


if __name__ == '__main__':
    main(sys.argv[1:])
