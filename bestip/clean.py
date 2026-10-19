#!/usr/bin/env python3
"""优选 IP/域名列表节点名规范化。

用法：
    python3 clean.py cname.txt ip.txt                      # 原地改写，保留原顺序
    python3 clean.py --url <优选列表URL> --prefix QMS -o cname.txt --append  # 拉取远端并合并进列表

规则：
    1. 删除空行、注释行；
    2. 按 地址:端口 去重（保留首次出现）；
    3. 节点名统一为 "<国旗> <地区>-<序号> [延迟]"，序号按原顺序（即延迟升序）；
    4. 无法识别地区时用 🌐 CF。
"""
import argparse
import os
import re
import sys
import urllib.request

FLAG = {
    'SG': '🇸🇬', 'JP': '🇯🇵', 'HK': '🇭🇰', 'TW': '🇹🇼', 'KR': '🇰🇷',
    'US': '🇺🇸', 'DE': '🇩🇪', 'GB': '🇬🇧', 'UK': '🇬🇧', 'NL': '🇳🇱',
    'FR': '🇫🇷', 'CA': '🇨🇦', 'AU': '🇦🇺', 'RU': '🇷🇺',
}

LABEL = {
    '三网': '3NET', '电信': 'CT', '联通': 'CU', '移动': 'CMCC',
    '亚洲': 'ASIA', '美洲': 'NA', '欧洲': 'EU', '香港': 'HK',
    '日本': 'JP', '新加坡': 'SG', '美国': 'US',
}

LINE_RE = re.compile(r'^(\[[0-9a-fA-F:]+\]|[\w.-]+)(:\d+)?$')


def clean(lines, default='CF'):
    seen, groups = set(), {}
    for raw in lines:
        line = raw.strip()
        if not line or line.startswith('#') or line.startswith('//'):
            continue
        addr, _, remark = line.partition('#')
        addr = addr.strip()
        if not LINE_RE.match(addr):
            continue
        key = addr.lower()
        if key in seen:
            continue
        seen.add(key)

        m = re.search(r'\b(SG|JP|HK|TW|KR|US|DE|GB|UK|NL|FR|CA|AU|RU)\b', remark.upper())
        if m:
            region = m.group(1)
        else:
            tag = next((v for k, v in LABEL.items() if k in remark), None)
            region = f'{default}-{tag}' if tag else f'{default}-IP'
        delay = re.search(r'(\d+\s*ms)', remark)
        groups.setdefault(region, []).append((addr, delay.group(1).replace(' ', '') if delay else ''))

    out = []
    for region, items in groups.items():
        flag = FLAG.get(region, '🌐')
        for i, (addr, delay) in enumerate(items, 1):
            name = region if len(items) == 1 else f'{region}-{i:02d}'
            suffix = f' {delay}' if delay else ''
            out.append(f'{addr}#{flag} {name}{suffix}')
    return out


def fetch(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    return urllib.request.urlopen(req, timeout=30).read().decode('utf-8', 'ignore').splitlines()


def main(argv):
    parser = argparse.ArgumentParser(description='优选列表节点名规范化')
    parser.add_argument('files', nargs='*', default=['cname.txt', 'ip.txt'])
    parser.add_argument('--url', help='改为从远程拉取并清洗')
    parser.add_argument('-o', '--out', help='配合 --url 使用的输出文件')
    parser.add_argument('--prefix', default='CF', help='无法识别地区时的名称前缀')
    parser.add_argument('--append', action='store_true', help='配合 --url：追加到 -o 指定文件，已存在的地址跳过')
    args = parser.parse_args(argv)

    if args.url:
        if not args.out:
            parser.error('--url 需要配合 -o/--out')
        result = clean(fetch(args.url), args.prefix)
        if args.append:
            existing = open(args.out, encoding='utf-8').read().splitlines() if os.path.exists(args.out) else []
            have = {line.partition('#')[0].strip().lower() for line in existing if line.strip()}
            result = [line for line in result if line.partition('#')[0].strip().lower() not in have]
            result = existing + result
        with open(args.out, 'w', encoding='utf-8') as f:
            f.write('\n'.join(result) + '\n')
        print(f'{args.out}: {len(result)} 条')
        return

    for path in args.files:
        with open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
        result = clean(lines, args.prefix)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(result) + '\n')
        print(f'{path}: {len(lines)} 行 -> {len(result)} 条')


if __name__ == '__main__':
    main(sys.argv[1:])
