#!/usr/bin/env python3
"""优选 IP/域名列表节点名规范化。

用法：
    python3 clean.py cname.txt ip.txt      # 原地改写，保留原顺序

规则：
    1. 删除空行、注释行；
    2. 按 地址:端口 去重（保留首次出现）；
    3. 节点名统一为 "<国旗> <地区>-<序号> [延迟]"，序号按原顺序（即延迟升序）；
    4. 无法识别地区时用 🌐 CF。
"""
import re
import sys

FLAG = {
    'SG': '🇸🇬', 'JP': '🇯🇵', 'HK': '🇭🇰', 'TW': '🇹🇼', 'KR': '🇰🇷',
    'US': '🇺🇸', 'DE': '🇩🇪', 'GB': '🇬🇧', 'UK': '🇬🇧', 'NL': '🇳🇱',
    'FR': '🇫🇷', 'CA': '🇨🇦', 'AU': '🇦🇺', 'RU': '🇷🇺',
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
        region = m.group(1) if m else default
        delay = re.search(r'\[(\d+\s*ms)\]', remark)
        groups.setdefault(region, []).append((addr, delay.group(1).replace(' ', '') if delay else ''))

    out = []
    for region, items in groups.items():
        flag = FLAG.get(region, '🌐')
        for i, (addr, delay) in enumerate(items, 1):
            name = region if len(items) == 1 else f'{region}-{i:02d}'
            suffix = f' {delay}' if delay else ''
            out.append(f'{addr}#{flag} {name}{suffix}')
    return out


def main(paths):
    for path in paths:
        with open(path, encoding='utf-8') as f:
            lines = f.read().splitlines()
        result = clean(lines)
        with open(path, 'w', encoding='utf-8') as f:
            f.write('\n'.join(result) + '\n')
        print(f'{path}: {len(lines)} 行 -> {len(result)} 条')


if __name__ == '__main__':
    main(sys.argv[1:] or ['cname.txt', 'ip.txt'])
