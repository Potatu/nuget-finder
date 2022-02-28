from dataclasses import dataclass
from typing import List
import click
import os
import xml.etree.ElementTree as ET
from tqdm import tqdm
import re

EXCLUDED_DIRECTORIES = set(['.git', 'bin', 'obj', '.idea', '.vscode', '.vs', '.rider', 'lib'])

version_regex = re.compile("(\d|\.)+") 

@dataclass(eq=True, frozen=True)
class Package():
    name: str
    version: str
    
    def __repr__(self) -> str:
        return f'Name:{self.name}, version:{self.version}'

@click.command()
@click.option('--dir', default=None, help='Directory to start crawling')
@click.option('--out', default=None, help='File to save results')

def main(dir, out):
    path = os.path.dirname(os.path.abspath(__file__)) if dir is None else dir
    click.echo(f'Start directory is \'{path}\'')
    with tqdm() as pbar:
        paths = get_paths([path], pbar)
    packages = set()
    for path in tqdm(paths, desc="Processing files"):
        try:
            for package in get_packages(path):
                packages.add(package)
        except Exception as e:
            print(f'Error. Skip file {path}')
    result = {}
    for package in packages:
        if package.name not in result:
            result[package.name] = []
        result[package.name].append(package.version)
    if out:
        with open(out, 'w+') as output:
            for name in result:
                output.write(f'{name}:{result[name]}\n')
            return
    else:
        for name in result:
            print(f'{name}:{result[name]}')
        

def get_packages(path: str) -> List[Package]:
    if path.endswith(".csproj"):
        return process_csproj(path)
    return process_packages_config(path)

def process_csproj(path:str) -> List[Package]:
    with open(path, mode='+r', encoding='utf-8') as file:
        tree = ET.parse(file)
        root = tree.getroot()
        if 'Sdk' in root.attrib:
            packages = []
            for reference in root.findall('ItemGroup/PackageReference'):
                if 'Include' in reference.attrib:
                    if 'Version' in reference.attrib and version_regex.match(reference.attrib['Version']):
                        packages.append(Package(reference.attrib['Include'], reference.attrib['Version']))
                    version = reference.find('Version')
                    if version is not None and version_regex.match(version.text):
                        packages.append(Package(reference.attrib['Include'], version.text))
            return packages
        return []


def process_packages_config(path: str) -> List[Package]:
    with open(path, mode='+r', encoding='utf-8') as file:
        tree = ET.parse(file)
        root = tree.getroot()
        result = []
        for reference in root.findall('package'):
            if(version_regex.match(reference.attrib['version'])):
                result.append(Package(reference.attrib['id'], reference.attrib['version']))
        return result



def get_paths(base_paths : List[str], pbar) -> List[str]:
    paths = []
    directories = []
    for base_path in base_paths:
        pbar.set_description(f'Procesing {base_path}')
        for item in os.listdir(base_path):
            if item in EXCLUDED_DIRECTORIES:
                continue
            full_path = os.path.join(base_path, item)
            if os.path.isfile(full_path):
                if item.endswith('.csproj') or item == 'packages.config':
                    paths.append(full_path)
            elif os.path.isdir(full_path):
                directories.append(full_path)
    
    return paths + get_paths(directories, pbar) if len(directories) >0 else paths


if __name__ == '__main__':
    main()