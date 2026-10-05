"""Edit a local Mihomo YAML; never connect to a router or fetch a subscription."""
import argparse
import copy
import json
import pathlib
import yaml

def apply(config, domains):
    result = copy.deepcopy(config)
    if not isinstance(result, dict):
        raise ValueError('Top-level YAML must be a mapping')
    rules = result.get('rules', [])
    if not isinstance(rules, list) or not all(isinstance(x, str) for x in rules):
        raise ValueError('rules must be a list of strings')
    targets = set(domains)
    remaining = []
    for rule in rules:
        parts = rule.split(',')
        if len(parts) >= 2 and parts[0].strip().upper() == 'DOMAIN-SUFFIX' and parts[1].strip() in targets:
            continue
        remaining.append(rule)
    result['rules'] = [f'DOMAIN-SUFFIX,{domain},DIRECT' for domain in domains] + remaining
    dns = result.setdefault('dns', {})
    if not isinstance(dns, dict):
        raise ValueError('dns must be a mapping')
    filters = dns.setdefault('fake-ip-filter', [])
    if not isinstance(filters, list):
        raise ValueError('dns.fake-ip-filter must be a list')
    for domain in domains:
        value = '+.' + domain
        if value not in filters:
            filters.append(value)
    return result

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('input', type=pathlib.Path)
    parser.add_argument('output', type=pathlib.Path)
    args = parser.parse_args()
    if args.input.resolve() == args.output.resolve():
        parser.error('Input and output must be different files')
    if args.output.exists():
        parser.error('Output already exists; choose a new filename')
    domains_path = pathlib.Path(__file__).resolve().parents[1] / 'examples' / 'naraka-domains.json'
    domains = json.loads(domains_path.read_text(encoding='utf-8'))
    config = yaml.safe_load(args.input.read_text(encoding='utf-8-sig'))
    result = apply(config, domains)
    with args.output.open('x', encoding='utf-8') as stream:
        yaml.safe_dump(result, stream, allow_unicode=True, sort_keys=False)
    print(f'Wrote {len(domains)} direct domain rules to {args.output}')

if __name__ == '__main__':
    main()
