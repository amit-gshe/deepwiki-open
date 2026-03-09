from api.data_pipeline import DatabaseManager  
  
# 1. 创建 DatabaseManager 实例  
db_manager = DatabaseManager()  
  
# 2. 设置仓库路径（必须先调用 _create_repo 或 prepare_database）  
db_manager._create_repo(  
    repo_url_or_path="/path/to/repo",  # 本地路径或远程URL  
    repo_type="local",  # 或 "gitlab", "bitbucket"  
    access_token=""  # 可选，用于私有仓库
)
  
# 3. 调用 prepare_db_index 方法  
documents = db_manager.prepare_db_index(  
    embedder_type="ollama",  # 可选：'openai', 'google', 'ollama'  
    excluded_dirs=[],  # 可选：排除的目录  
    excluded_files=[]  # 可选：排除的文件模式  
)