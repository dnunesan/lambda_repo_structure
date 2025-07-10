import requests
import os
import json
import time
from typing import Dict, List, Optional, Any
from datetime import datetime
import logging
from urllib.parse import urlparse, urljoin
import re

class RepositoryScraper:
    """
    Servicio para hacer scraping de repositorios Git (GitHub, GitLab, etc.)
    """
    
    def __init__(self, token: Optional[str] = None):
        self.session = requests.Session()
        self.token = token
        self.base_headers = {
            'User-Agent': 'Repository-Scraper/1.0',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        if token:
            self.base_headers['Authorization'] = f'token {token}'
        
        self.session.headers.update(self.base_headers)
        self.logger = self._setup_logger()
        
    def _setup_logger(self) -> logging.Logger:
        """Configura el logger para el servicio"""
        logger = logging.getLogger('RepositoryScraper')
        logger.setLevel(logging.INFO)
        
        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger
    
    def _parse_repo_url(self, repo_url: str) -> Dict[str, str]:
        """Extrae información de la URL del repositorio"""
        parsed = urlparse(repo_url)
        
        # Patrón para GitHub/GitLab: /owner/repo
        path_parts = parsed.path.strip('/').split('/')
        
        if len(path_parts) < 2:
            raise ValueError("URL de repositorio inválida")
        
        return {
            'platform': parsed.netloc.lower(),
            'owner': path_parts[0],
            'repo': path_parts[1].replace('.git', ''),
            'base_url': f"{parsed.scheme}://{parsed.netloc}"
        }
    
    def _get_api_url(self, platform: str, owner: str, repo: str) -> str:
        """Genera la URL de la API según la plataforma"""
        if 'github.com' in platform:
            return f"https://api.github.com/repos/{owner}/{repo}"
        elif 'gitlab.com' in platform:
            return f"https://gitlab.com/api/v4/projects/{owner}%2F{repo}"
        else:
            raise ValueError(f"Plataforma no soportada: {platform}")
    
    def scrape_repository_info(self, repo_url: str) -> Dict[str, Any]:
        """
        Extrae información básica del repositorio
        """
        try:
            repo_info = self._parse_repo_url(repo_url)
            api_url = self._get_api_url(
                repo_info['platform'], 
                repo_info['owner'], 
                repo_info['repo']
            )
            
            self.logger.info(f"Obteniendo información de: {repo_url}")
            response = self._make_request(api_url)
            
            if 'github.com' in repo_info['platform']:
                return self._parse_github_repo(response)
            elif 'gitlab.com' in repo_info['platform']:
                return self._parse_gitlab_repo(response)
            
        except Exception as e:
            self.logger.error(f"Error al obtener información del repositorio: {e}")
            return {}
    
    def _parse_github_repo(self, data: Dict) -> Dict[str, Any]:
        """Parsea la respuesta de la API de GitHub"""
        return {
            'name': data.get('name'),
            'full_name': data.get('full_name'),
            'description': data.get('description'),
            'language': data.get('language'),
            'stars': data.get('stargazers_count', 0),
            'forks': data.get('forks_count', 0),
            'watchers': data.get('watchers_count', 0),
            'issues': data.get('open_issues_count', 0),
            'created_at': data.get('created_at'),
            'updated_at': data.get('updated_at'),
            'size': data.get('size', 0),
            'default_branch': data.get('default_branch'),
            'topics': data.get('topics', []),
            'license': data.get('license', {}).get('name') if data.get('license') else None,
            'clone_url': data.get('clone_url'),
            'ssh_url': data.get('ssh_url'),
            'homepage': data.get('homepage'),
            'archived': data.get('archived', False),
            'disabled': data.get('disabled', False),
            'private': data.get('private', False)
        }
    
    def _parse_gitlab_repo(self, data: Dict) -> Dict[str, Any]:
        """Parsea la respuesta de la API de GitLab"""
        return {
            'name': data.get('name'),
            'full_name': data.get('path_with_namespace'),
            'description': data.get('description'),
            'language': None,  # GitLab no proporciona esto directamente
            'stars': data.get('star_count', 0),
            'forks': data.get('forks_count', 0),
            'watchers': 0,  # GitLab no tiene watchers
            'issues': data.get('open_issues_count', 0),
            'created_at': data.get('created_at'),
            'updated_at': data.get('last_activity_at'),
            'size': 0,  # No disponible en GitLab API v4
            'default_branch': data.get('default_branch'),
            'topics': data.get('topics', []),
            'license': None,  # Requiere llamada adicional
            'clone_url': data.get('http_url_to_repo'),
            'ssh_url': data.get('ssh_url_to_repo'),
            'homepage': data.get('web_url'),
            'archived': data.get('archived', False),
            'disabled': False,
            'private': data.get('visibility') == 'private'
        }
    
    def scrape_file_structure(self, repo_url: str, path: str = "") -> List[Dict[str, Any]]:
        """
        Extrae la estructura de archivos del repositorio
        """
        try:
            repo_info = self._parse_repo_url(repo_url)
            
            if 'github.com' in repo_info['platform']:
                api_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/contents/{path}"
            elif 'gitlab.com' in repo_info['platform']:
                api_url = f"https://gitlab.com/api/v4/projects/{repo_info['owner']}%2F{repo_info['repo']}/repository/tree"
                if path:
                    api_url += f"?path={path}"
            
            response = self._make_request(api_url)
            
            if isinstance(response, list):
                return [self._parse_file_info(item, repo_info['platform']) for item in response]
            else:
                return [self._parse_file_info(response, repo_info['platform'])]
                
        except Exception as e:
            self.logger.error(f"Error al obtener estructura de archivos: {e}")
            return []
    
    def _parse_file_info(self, item: Dict, platform: str) -> Dict[str, Any]:
        """Parsea información de archivos/directorios"""
        if 'github.com' in platform:
            return {
                'name': item.get('name'),
                'path': item.get('path'),
                'type': item.get('type'),  # file, dir
                'size': item.get('size', 0),
                'download_url': item.get('download_url'),
                'url': item.get('url')
            }
        else:  # GitLab
            return {
                'name': item.get('name'),
                'path': item.get('path'),
                'type': item.get('type'),  # blob, tree
                'size': 0,  # No disponible
                'download_url': None,
                'url': item.get('web_url')
            }
    
    def scrape_commits(self, repo_url: str, limit: int = 30) -> List[Dict[str, Any]]:
        """
        Extrae información de commits recientes
        """
        try:
            repo_info = self._parse_repo_url(repo_url)
            
            if 'github.com' in repo_info['platform']:
                api_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/commits"
            elif 'gitlab.com' in repo_info['platform']:
                api_url = f"https://gitlab.com/api/v4/projects/{repo_info['owner']}%2F{repo_info['repo']}/repository/commits"
            
            params = {'per_page': limit}
            response = self._make_request(api_url, params=params)
            
            return [self._parse_commit_info(commit, repo_info['platform']) for commit in response]
            
        except Exception as e:
            self.logger.error(f"Error al obtener commits: {e}")
            return []
    
    def _parse_commit_info(self, commit: Dict, platform: str) -> Dict[str, Any]:
        """Parsea información de commits"""
        if 'github.com' in platform:
            return {
                'sha': commit.get('sha'),
                'message': commit.get('commit', {}).get('message'),
                'author': commit.get('commit', {}).get('author', {}).get('name'),
                'author_email': commit.get('commit', {}).get('author', {}).get('email'),
                'date': commit.get('commit', {}).get('author', {}).get('date'),
                'url': commit.get('html_url')
            }
        else:  # GitLab
            return {
                'sha': commit.get('id'),
                'message': commit.get('message'),
                'author': commit.get('author_name'),
                'author_email': commit.get('author_email'),
                'date': commit.get('created_at'),
                'url': commit.get('web_url')
            }
    
    def scrape_issues(self, repo_url: str, state: str = "open", limit: int = 30) -> List[Dict[str, Any]]:
        """
        Extrae información de issues
        """
        try:
            repo_info = self._parse_repo_url(repo_url)
            
            if 'github.com' in repo_info['platform']:
                api_url = f"https://api.github.com/repos/{repo_info['owner']}/{repo_info['repo']}/issues"
            elif 'gitlab.com' in repo_info['platform']:
                api_url = f"https://gitlab.com/api/v4/projects/{repo_info['owner']}%2F{repo_info['repo']}/issues"
            
            params = {'state': state, 'per_page': limit}
            response = self._make_request(api_url, params=params)
            
            return [self._parse_issue_info(issue, repo_info['platform']) for issue in response]
            
        except Exception as e:
            self.logger.error(f"Error al obtener issues: {e}")
            return []
    
    def _parse_issue_info(self, issue: Dict, platform: str) -> Dict[str, Any]:
        """Parsea información de issues"""
        if 'github.com' in platform:
            return {
                'number': issue.get('number'),
                'title': issue.get('title'),
                'body': issue.get('body'),
                'state': issue.get('state'),
                'author': issue.get('user', {}).get('login'),
                'created_at': issue.get('created_at'),
                'updated_at': issue.get('updated_at'),
                'labels': [label.get('name') for label in issue.get('labels', [])],
                'url': issue.get('html_url')
            }
        else:  # GitLab
            return {
                'number': issue.get('iid'),
                'title': issue.get('title'),
                'body': issue.get('description'),
                'state': issue.get('state'),
                'author': issue.get('author', {}).get('username'),
                'created_at': issue.get('created_at'),
                'updated_at': issue.get('updated_at'),
                'labels': issue.get('labels', []),
                'url': issue.get('web_url')
            }
    
    def _make_request(self, url: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Realiza petición HTTP con manejo de errores y rate limiting"""
        max_retries = 3
        retry_delay = 1
        
        for attempt in range(max_retries):
            try:
                response = self.session.get(url, params=params, timeout=30)
                
                if response.status_code == 403:
                    self.logger.warning("Rate limit alcanzado, esperando...")
                    time.sleep(60)
                    continue
                
                response.raise_for_status()
                return response.json()
                
            except requests.exceptions.RequestException as e:
                if attempt < max_retries - 1:
                    self.logger.warning(f"Intento {attempt + 1} falló, reintentando en {retry_delay}s")
                    time.sleep(retry_delay)
                    retry_delay *= 2
                else:
                    raise e
    
    def scrape_full_repository(self, repo_url: str) -> Dict[str, Any]:
        """
        Realiza un scraping completo del repositorio
        """
        self.logger.info(f"Iniciando scraping completo de: {repo_url}")
        
        result = {
            'scraped_at': datetime.now().isoformat(),
            'repository_url': repo_url,
            'basic_info': {},
            'file_structure': [],
            'recent_commits': [],
            'open_issues': [],
            'closed_issues': []
        }
        
        # Información básica
        result['basic_info'] = self.scrape_repository_info(repo_url)
        
        # Estructura de archivos
        result['file_structure'] = self.scrape_file_structure(repo_url)
        
        # Commits recientes
        result['recent_commits'] = self.scrape_commits(repo_url, limit=50)
        
        # Issues abiertas
        result['open_issues'] = self.scrape_issues(repo_url, state="open", limit=50)
        
        # Issues cerradas
        result['closed_issues'] = self.scrape_issues(repo_url, state="closed", limit=20)
        
        self.logger.info("Scraping completo finalizado")
        return result


# Ejemplo de uso
if __name__ == "__main__":
    # Inicializar el scraper (opcionalmente con token de GitHub)
    # scraper = RepositoryScraper(token="tu_github_token_aqui")
    scraper = RepositoryScraper()
    
    # URL del repositorio a scrapear
    repo_url = "https://github.com/microsoft/vscode"
    
    # Scraping completo
    data = scraper.scrape_full_repository(repo_url)
    
    # También puedes usar métodos individuales
    print("=== Información básica ===")
    basic_info = scraper.scrape_repository_info(repo_url)
    print(json.dumps(basic_info, indent=2))
    
    print("\n=== Estructura de archivos (raíz) ===")
    files = scraper.scrape_file_structure(repo_url)
    for file in files[:5]:  # Mostrar solo los primeros 5
        print(f"- {file['name']} ({file['type']})")
    
    print("\n=== Commits recientes ===")
    commits = scraper.scrape_commits(repo_url, limit=5)
    for commit in commits:
        print(f"- {commit['message'][:50]}... por {commit['author']}")