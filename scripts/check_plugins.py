#!/usr/bin/env python3
"""Offline plugin configuration checks; versions are compared within each plugin."""
import argparse
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit
import yaml

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'plugins/berkshire-team/skills/berkshire-team/scripts'))
from delivery_dependencies import strict_json


class UniqueLoader(yaml.SafeLoader):
    pass


def unique_mapping(loader, node, deep=False):
    result={}
    for key_node,value_node in node.value:
        key=loader.construct_object(key_node,deep=deep)
        if key in result:raise ValueError('duplicate YAML key: '+str(key))
        result[key]=loader.construct_object(value_node,deep=deep)
    return result


UniqueLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG,unique_mapping)


def check(root):
    root=Path(root).resolve();issues=[];versions={};checked=[]
    def require(condition,message):
        if not condition:raise ValueError(message)
    def nonempty(value):return isinstance(value,str) and bool(value.strip())
    def local(base,value,directory=False):
        require(nonempty(value),'path must be a nonempty string')
        require(not Path(value).is_absolute(),'absolute package path forbidden: '+value)
        path=base/value
        require(path.resolve().is_relative_to(root),'path escapes repository: '+value)
        require(not any(p.is_symlink() for p in [path,*path.parents] if p.is_relative_to(root)),'symlink path: '+value)
        require(path.is_dir() if directory else path.is_file(),'missing path: '+str(path.relative_to(root)))
        if not directory:require(bool(path.read_bytes().strip()),'empty file: '+value)
        checked.append(str(path.relative_to(root)));return path
    def read(path):
        value=strict_json(path.read_text(encoding='utf-8'))
        require(isinstance(value,dict),'configuration must be object: '+str(path));return value
    try:
        market=read(local(root,'.agents/plugins/marketplace.json'))
        require(nonempty(market.get('name')),'marketplace name required')
        require(nonempty(market.get('interface',{}).get('displayName')),'marketplace displayName required')
        entries=market.get('plugins');require(isinstance(entries,list) and entries,'marketplace plugins required')
        require(len({e['name'] for e in entries})==len(entries),'duplicate marketplace plugin')
        plugin_dirs={p.name for p in (root/'plugins').iterdir() if p.is_dir() and not p.name.startswith('.')}
        require({e['name'] for e in entries}==plugin_dirs,'marketplace must list each packaged plugin exactly once')
    except (OSError,ValueError,KeyError,TypeError,AttributeError) as exc:
        return dict(status='FAIL',issues=[dict(artifact='.agents/plugins/marketplace.json',reason=str(exc))],plugins={},checked_paths=checked)
    for entry in entries:
        name=entry.get('name','unknown')
        try:
            require(entry['source']['source']=='local','packaged marketplace source must be local')
            package=local(root,entry['source']['path'],True)
            require(package.name==name,'marketplace source does not match plugin identity')
            portable=read(local(package,'plugin.json'));compat=read(local(package,'.codex-plugin/plugin.json'))
            for config in (portable,compat):
                require(config.get('name')==name,'plugin name mismatch')
                require(nonempty(config.get('description')),'plugin description required')
                require(isinstance(config.get('version'),str) and re.fullmatch(r'\d+\.\d+\.\d+(?:-[0-9A-Za-z.-]+)?',config['version']),'invalid semantic version')
            require(portable['version']==compat['version'],'same-plugin version mismatch')
            versions[name]=portable['version']
            readme=(root/'README.md').read_text(encoding='utf-8')
            patterns={'berkshire-team':[r'Berkshire Team (\d+\.\d+\.\d+)', r'伯克希尔团队 (\d+\.\d+\.\d+)'],
                      'ai-value-investing-agents':[r'AI Value Investing Agents \(AIVA\) (\d+\.\d+\.\d+)', r'AI Value Investing Agents（AIVA）(\d+\.\d+\.\d+)']}
            for pattern in patterns.get(name,[]):
                for version in re.findall(pattern,readme):
                    require(version==portable['version'],'repository README current version mismatch: '+name)
            if 'version' in entry:require(entry['version']==portable['version'],'marketplace plugin version mismatch')
            require(portable.get('$schema')=='https://agent-plugins.org/schemas/1.0.0/plugin.schema.json','portable manifest schema required')
            interface=portable['extensions']['com.openai']['interface']
            for config_interface in (interface,compat['interface']):
                for field in ('displayName','shortDescription','longDescription','category'):
                    require(nonempty(config_interface.get(field)),field+' required')
                require(isinstance(config_interface.get('capabilities'),list) and config_interface['capabilities'],'capabilities required')
                prompt=config_interface.get('defaultPrompt')
                require(nonempty(prompt) or isinstance(prompt,list) and 1<=len(prompt)<=3 and all(nonempty(p) for p in prompt),'defaultPrompt required')
                for field in ('logo','composerIcon','logoDark','composerIconDark'):
                    if field in config_interface:local(package,config_interface[field])
            require(interface==compat['interface'],'portable/compat interface mismatch')
            skills=local(package,compat['skills'],True)
            require(skills.resolve()==(package/'skills').resolve(),'skills entry must be portable skills directory')
            skill_files=sorted(skills.glob('*/SKILL.md'));require(skill_files,'no skill entrypoints')
            for directory in skills.iterdir():
                if directory.is_dir() and not directory.name.startswith('.'):
                    local(directory,'SKILL.md')
            for skill in skill_files:
                local(root,str(skill.relative_to(root)))
                text=skill.read_text(encoding='utf-8')
                front=re.match(r'\A---\s*\n(.*?)\n---(?:\s*\n|$)',text,re.S)
                require(front is not None,'missing skill YAML frontmatter: '+str(skill))
                meta=yaml.load(front.group(1),Loader=UniqueLoader)
                require(isinstance(meta,dict) and meta.get('name')==skill.parent.name,'skill name mismatch: '+str(skill))
                require(nonempty(meta.get('description')),'skill description missing: '+str(skill))
                agent=local(skill.parent,'agents/openai.yaml')
                ui=yaml.load(agent.read_text(encoding='utf-8'),Loader=UniqueLoader)
                require(isinstance(ui,dict) and isinstance(ui.get('interface'),dict),'invalid agent UI YAML: '+str(agent))
                for field in ('display_name','short_description','default_prompt'):
                    require(nonempty(ui['interface'].get(field)),'missing '+field+': '+str(agent))
            upstream=package/'UPSTREAM.json'
            if upstream.exists():
                record=read(upstream)
                if 'local_package_version' in record:require(record['local_package_version']==portable['version'],'UPSTREAM local package version mismatch')
            # Current title only; changelogs and upstream release versions are intentionally independent.
            title=(package/'README.md').read_text(encoding='utf-8').splitlines()[0]
            match=re.search(r'\b(\d+\.\d+\.\d+)\b',title)
            if match:require(match.group(1)==portable['version'],'README current version mismatch')
            # Local Markdown references in the maintained Berkshire workflow and entrypoint README.
            documents=[package/'README.md'] if name=='berkshire-team' else []
            if name=='berkshire-team':documents+=list(skills.rglob('*.md'))
            for doc in documents:
                text=re.sub(r'```.*?```','',doc.read_text(encoding='utf-8'),flags=re.S)
                for target in re.findall(r'\]\(([^)]+)\)',text):
                    url=urlsplit(target)
                    if not url.scheme and url.path:
                        local(doc.parent,unquote(url.path))
            # Manifest-declared optional integrations must exist if declared.
            for config in (portable.get('extensions',{}).get('com.openai',{}),compat):
                for field in ('apps','mcpServers','hooks'):
                    if field in config and config[field] is not None:
                        path=local(package,config[field]);read(path)
        except (OSError,ValueError,KeyError,TypeError,AttributeError,yaml.YAMLError) as exc:
            issues.append(dict(artifact='plugins/'+name,reason=str(exc)))
    return dict(status='FAIL' if issues else 'PASS',issues=issues,plugins=versions,checked_paths=sorted(set(checked)))


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--root',default=str(ROOT));args=parser.parse_args()
    result=check(args.root);print(json.dumps(result,ensure_ascii=False,indent=2));return 1 if result['issues'] else 0


if __name__=='__main__':raise SystemExit(main())
